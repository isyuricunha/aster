import json

import httpx

from app.openai_compatible import OpenAICompatibleClient


async def test_profile_parameters_are_sent_only_when_configured() -> None:
    received: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        received["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            text='data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n',
            headers={"Content-Type": "text/event-stream"},
        )

    client = OpenAICompatibleClient(transport=httpx.MockTransport(handler))
    chunks = [
        chunk
        async for chunk in client.stream_chat_completion(
            base_url="https://example.com/v1",
            api_key=None,
            model_id="reasoning-model",
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.2,
            top_p=0.85,
            max_output_tokens=4096,
            token_parameter="max_completion_tokens",
            reasoning_effort="high",
        )
    ]

    assert chunks == ["ok"]
    assert received["payload"] == {
        "model": "reasoning-model",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
        "temperature": 0.2,
        "top_p": 0.85,
        "max_completion_tokens": 4096,
        "reasoning_effort": "high",
    }
