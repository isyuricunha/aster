from collections.abc import Iterable

import httpx


class ModelEndpointError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._transport = transport

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Aster/0.1",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                response = await client.get(f"{base_url}/models", headers=headers)
        except httpx.TimeoutException as error:
            raise ModelEndpointError(
                "timeout", "The endpoint did not respond before the timeout."
            ) from error
        except httpx.RequestError as error:
            raise ModelEndpointError(
                "connection_error", "The endpoint could not be reached."
            ) from error

        if response.status_code in {401, 403}:
            raise ModelEndpointError(
                "authentication_failed",
                f"The endpoint returned HTTP {response.status_code}.",
                response.status_code,
            )
        if response.status_code == 404:
            raise ModelEndpointError(
                "models_not_supported",
                "The endpoint does not expose a compatible /models route.",
                422,
            )
        if response.is_error:
            raise ModelEndpointError(
                "upstream_error",
                f"The endpoint returned HTTP {response.status_code}.",
                502,
            )

        try:
            payload = response.json()
        except ValueError as error:
            raise ModelEndpointError(
                "invalid_response", "The endpoint returned invalid JSON."
            ) from error

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ModelEndpointError(
                "invalid_response", "The endpoint response does not contain a model list."
            )

        model_ids = self._extract_model_ids(data)
        if not model_ids:
            return []
        return sorted(set(model_ids), key=str.casefold)

    @staticmethod
    def _extract_model_ids(items: Iterable[object]) -> list[str]:
        model_ids: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip():
                model_ids.append(model_id.strip())
        return model_ids
