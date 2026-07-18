import json

import httpx
import pytest

from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient


async def test_stream_chat_completion_yields_text_and_sends_canonical_roles() -> None:
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["authorization"] = request.headers.get("Authorization")
        received["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            text=(
                'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
                'data: {"choices":[{"delta":{"content":[{"text":" world"}]}}]}\n\n'
                "data: [DONE]\n\n"
            ),
            headers={"Content-Type": "text/event-stream"},
        )

    client = OpenAICompatibleClient(transport=httpx.MockTransport(handler))
    chunks = [
        chunk
        async for chunk in client.stream_chat_completion(
            base_url="https://example.com/v1",
            api_key="secret",
            model_id="chat-model",
            messages=[
                {"role": "developer", "content": "Persona"},
                {"role": "user", "content": "Hi"},
            ],
        )
    ]

    assert chunks == ["Hello", " world"]
    assert received["authorization"] == "Bearer secret"
    assert received["payload"] == {
        "model": "chat-model",
        "messages": [
            {"role": "system", "content": "Persona"},
            {"role": "user", "content": "Hi"},
        ],
        "stream": True,
    }


async def test_stream_chat_completion_sanitizes_upstream_errors() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(500, text="secret upstream body"))
    client = OpenAICompatibleClient(transport=transport)

    with pytest.raises(ModelEndpointError) as raised:
        _ = [
            chunk
            async for chunk in client.stream_chat_completion(
                base_url="https://example.com/v1",
                api_key=None,
                model_id="chat-model",
                messages=[{"role": "user", "content": "Hi"}],
            )
        ]

    assert raised.value.code == "upstream_error"
    assert raised.value.message == "The endpoint returned HTTP 500."
    assert "secret upstream body" not in raised.value.message
