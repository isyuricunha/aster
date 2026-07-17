import base64
import binascii
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from app.openai_compatible import ModelEndpointError


@dataclass(frozen=True, slots=True)
class ProviderImage:
    data: bytes
    revised_prompt: str | None = None


class OpenAICompatibleImageClient:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_output_bytes: int,
        max_outputs: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_output_bytes = max_output_bytes
        self._max_outputs = max_outputs
        self._transport = transport

    @staticmethod
    def _headers(api_key: str | None) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "Aster/0.7"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def generate(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model_id: str,
        prompt: str,
        parameters: dict[str, object],
    ) -> list[ProviderImage]:
        payload = {"model": model_id, "prompt": prompt, **parameters}
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{base_url}/images/generations",
                    headers=self._headers(api_key),
                    json=payload,
                )
        except httpx.TimeoutException as error:
            raise ModelEndpointError(
                "timeout", "The image endpoint did not respond before the timeout."
            ) from error
        except httpx.RequestError as error:
            raise ModelEndpointError(
                "connection_error", "The image endpoint could not be reached."
            ) from error
        self._raise_for_status(response, route="/images/generations")
        return await self._parse_response(response, api_key=api_key)

    async def edit(
        self,
        *,
        base_url: str,
        api_key: str | None,
        model_id: str,
        prompt: str,
        images: list[tuple[str, bytes, str]],
        mask: tuple[str, bytes, str] | None,
        parameters: dict[str, object],
    ) -> list[ProviderImage]:
        fields: list[tuple[str, str]] = [("model", model_id), ("prompt", prompt)]
        for key, value in parameters.items():
            fields.append((key, self._multipart_value(value)))
        files: list[tuple[str, tuple[str, bytes, str]]] = [
            ("image", (filename, data, media_type)) for filename, data, media_type in images
        ]
        if mask is not None:
            files.append(("mask", mask))
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    f"{base_url}/images/edits",
                    headers=self._headers(api_key),
                    data=fields,
                    files=files,
                )
        except httpx.TimeoutException as error:
            raise ModelEndpointError(
                "timeout", "The image edit endpoint did not respond before the timeout."
            ) from error
        except httpx.RequestError as error:
            raise ModelEndpointError(
                "connection_error", "The image edit endpoint could not be reached."
            ) from error
        self._raise_for_status(response, route="/images/edits")
        return await self._parse_response(response, api_key=api_key)

    @staticmethod
    def _multipart_value(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str | int | float):
            return str(value)
        import json

        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    async def _parse_response(
        self,
        response: httpx.Response,
        *,
        api_key: str | None,
    ) -> list[ProviderImage]:
        try:
            payload = response.json()
        except ValueError as error:
            raise ModelEndpointError(
                "invalid_response", "The image endpoint returned invalid JSON."
            ) from error
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list) or not data:
            raise ModelEndpointError(
                "invalid_response", "The image endpoint did not return any images."
            )
        if len(data) > self._max_outputs:
            raise ModelEndpointError(
                "invalid_response",
                f"The image endpoint returned more than {self._max_outputs} images.",
            )
        images: list[ProviderImage] = []
        for item in data:
            if not isinstance(item, dict):
                raise ModelEndpointError(
                    "invalid_response", "The image endpoint returned an invalid image item."
                )
            revised_prompt = item.get("revised_prompt")
            if not isinstance(revised_prompt, str):
                revised_prompt = None
            encoded = item.get("b64_json")
            url = item.get("url")
            if isinstance(encoded, str):
                image_data = self._decode_base64(encoded)
            elif isinstance(url, str):
                image_data = await self._download(url, api_key=api_key)
            else:
                raise ModelEndpointError(
                    "invalid_response",
                    "The image endpoint returned neither base64 data nor a URL.",
                )
            images.append(ProviderImage(data=image_data, revised_prompt=revised_prompt))
        return images

    def _decode_base64(self, value: str) -> bytes:
        estimated = len(value) * 3 // 4
        if estimated > self._max_output_bytes:
            raise ModelEndpointError(
                "output_too_large", "The generated image exceeds the configured byte limit."
            )
        try:
            decoded = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ModelEndpointError(
                "invalid_response", "The image endpoint returned invalid base64 data."
            ) from error
        if not decoded or len(decoded) > self._max_output_bytes:
            raise ModelEndpointError(
                "output_too_large", "The generated image exceeds the configured byte limit."
            )
        return decoded

    async def _download(self, url: str, *, api_key: str | None) -> bytes:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ModelEndpointError(
                "invalid_response", "The image endpoint returned an invalid download URL."
            )
        headers = {"Accept": "image/*", "User-Agent": "Aster/0.7"}
        if api_key and parsed.path.startswith("/v1/"):
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                transport=self._transport,
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    self._raise_for_status(response, route="image download")
                    output = bytearray()
                    async for chunk in response.aiter_bytes():
                        output.extend(chunk)
                        if len(output) > self._max_output_bytes:
                            raise ModelEndpointError(
                                "output_too_large",
                                "The generated image exceeds the configured byte limit.",
                            )
        except ModelEndpointError:
            raise
        except httpx.TimeoutException as error:
            raise ModelEndpointError(
                "timeout", "The generated image download timed out."
            ) from error
        except httpx.RequestError as error:
            raise ModelEndpointError(
                "connection_error", "The generated image could not be downloaded."
            ) from error
        if not output:
            raise ModelEndpointError(
                "invalid_response", "The generated image download was empty."
            )
        return bytes(output)

    @staticmethod
    def _raise_for_status(response: httpx.Response, *, route: str) -> None:
        if response.status_code in {401, 403}:
            raise ModelEndpointError(
                "authentication_failed",
                f"The image endpoint returned HTTP {response.status_code}.",
                response.status_code,
            )
        if response.status_code == 404:
            raise ModelEndpointError(
                "images_not_supported",
                f"The endpoint does not expose a compatible {route} route.",
                422,
            )
        if response.status_code == 429:
            raise ModelEndpointError(
                "rate_limited", "The image endpoint is temporarily rate limited.", 429
            )
        if response.status_code in {400, 409, 413, 415, 422}:
            raise ModelEndpointError(
                "request_rejected",
                f"The image endpoint rejected the request with HTTP {response.status_code}.",
                response.status_code,
            )
        if response.is_error:
            raise ModelEndpointError(
                "upstream_error", f"The image endpoint returned HTTP {response.status_code}."
            )
