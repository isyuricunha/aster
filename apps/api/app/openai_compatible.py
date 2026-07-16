import json
from collections.abc import AsyncIterator, Iterable, Sequence

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
        stream_timeout_seconds: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._stream_timeout = httpx.Timeout(
            stream_timeout_seconds,
            connect=timeout_seconds,
        )
        self._transport = transport

    @staticmethod
    def _headers(api_key: str | None) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Aster/0.4",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def list_models(self, base_url: str, api_key: str | None) -> list[str]:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                response = await client.get(f"{base_url}/models", headers=self._headers(api_key))
        except httpx.TimeoutException as error:
            raise ModelEndpointError(
                "timeout", "The endpoint did not respond before the timeout."
            ) from error
        except httpx.RequestError as error:
            raise ModelEndpointError(
                "connection_error", "The endpoint could not be reached."
            ) from error

        self._raise_for_status(response, route_name="models")

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

    async def stream_chat_completion(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model_id: str,
        messages: Sequence[dict[str, str]],
    ) -> AsyncIterator[str]:
        payload = {
            "model": model_id,
            "messages": list(messages),
            "stream": True,
        }
        headers = self._headers(api_key)
        headers["Accept"] = "text/event-stream"

        try:
            async with httpx.AsyncClient(
                timeout=self._stream_timeout,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                async with client.stream(
                    "POST",
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    self._raise_for_status(response, route_name="chat")
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data:
                            continue
                        if data == "[DONE]":
                            return
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError as error:
                            raise ModelEndpointError(
                                "invalid_response",
                                "The endpoint returned an invalid streaming event.",
                            ) from error
                        if isinstance(event, dict) and event.get("error") is not None:
                            raise ModelEndpointError(
                                "upstream_error",
                                "The endpoint reported an error while streaming the response.",
                            )
                        content = self._extract_delta_content(event)
                        if content:
                            yield content
        except httpx.TimeoutException as error:
            raise ModelEndpointError(
                "timeout", "The endpoint did not respond before the timeout."
            ) from error
        except httpx.RequestError as error:
            raise ModelEndpointError(
                "connection_error", "The endpoint could not be reached."
            ) from error

    @staticmethod
    def _raise_for_status(response: httpx.Response, *, route_name: str) -> None:
        if response.status_code in {401, 403}:
            raise ModelEndpointError(
                "authentication_failed",
                f"The endpoint returned HTTP {response.status_code}.",
                response.status_code,
            )
        if response.status_code == 404:
            code = "models_not_supported" if route_name == "models" else "chat_not_supported"
            route = "/models" if route_name == "models" else "/chat/completions"
            raise ModelEndpointError(
                code,
                f"The endpoint does not expose a compatible {route} route.",
                422,
            )
        if response.is_error:
            raise ModelEndpointError(
                "upstream_error",
                f"The endpoint returned HTTP {response.status_code}.",
            )

    @staticmethod
    def _extract_delta_content(event: object) -> str:
        if not isinstance(event, dict):
            return ""
        choices = event.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        choice = choices[0]
        if not isinstance(choice, dict):
            return ""
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            return ""
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""

        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)

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
