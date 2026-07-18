import json

import httpx
import pytest

from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient
from app.provider_instruction_roles import (
    clear_provider_instruction_roles,
    register_provider_instruction_role,
)


@pytest.mark.asyncio
async def test_list_models_uses_bearer_auth_and_normalizes_ids() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://models.example/v1/models"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={"data": [{"id": " model-b "}, {"id": "model-a"}, {"id": "model-a"}]},
        )

    client = OpenAICompatibleClient(transport=httpx.MockTransport(handler))
    assert await client.list_models("https://models.example/v1", "test-key") == [
        "model-a",
        "model-b",
    ]


@pytest.mark.asyncio
async def test_list_models_returns_sanitized_authentication_error() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(401, text="secret upstream body"))
    client = OpenAICompatibleClient(transport=transport)

    with pytest.raises(ModelEndpointError) as raised:
        await client.list_models("https://models.example/v1", "bad-key")

    assert raised.value.code == "authentication_failed"
    assert "secret upstream body" not in raised.value.message


@pytest.mark.asyncio
async def test_chat_instruction_roles_default_to_system_and_allow_developer_opt_in() -> None:
    payloads: list[dict[str, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        return httpx.Response(
            200,
            text="data: [DONE]\n\n",
            headers={"Content-Type": "text/event-stream"},
        )

    clear_provider_instruction_roles()
    client = OpenAICompatibleClient(transport=httpx.MockTransport(handler))
    assert [
        item
        async for item in client.stream_chat_completion(
            base_url="https://models.example/v1",
            api_key=None,
            model_id="system-model",
            messages=[
                {"role": "developer", "content": "Internal instruction"},
                {"role": "user", "content": "Hello"},
            ],
        )
    ] == []
    assert payloads[-1]["messages"] == [
        {"role": "system", "content": "Internal instruction"},
        {"role": "user", "content": "Hello"},
    ]

    register_provider_instruction_role(
        base_url="https://models.example/v1",
        model_id="developer-model",
        instruction_role="developer",
    )
    assert [
        item
        async for item in client.stream_chat_completion(
            base_url="https://models.example/v1",
            api_key=None,
            model_id="developer-model",
            messages=[
                {"role": "system", "content": "Internal instruction"},
                {"role": "user", "content": "Hello"},
            ],
        )
    ] == []
    assert payloads[-1]["messages"] == [
        {"role": "developer", "content": "Internal instruction"},
        {"role": "user", "content": "Hello"},
    ]
    clear_provider_instruction_roles()


@pytest.mark.asyncio
async def test_stream_chat_completion_parses_fragmented_tool_calls() -> None:
    tool_definition = {
        "type": "function",
        "function": {
            "name": "mcp_echo",
            "description": "Echo a value.",
            "parameters": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        },
    }
    events = [
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "mcp_echo",
                                    "arguments": '{"value":',
                                },
                            }
                        ]
                    },
                    "finish_reason": None,
                }
            ]
        },
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {"arguments": '"hello"}'},
                            }
                        ]
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
    ]
    stream = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
    stream += "data: [DONE]\n\n"

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://models.example/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["tools"] == [tool_definition]
        assert payload["tool_choice"] == "auto"
        return httpx.Response(
            200,
            text=stream,
            headers={"Content-Type": "text/event-stream"},
        )

    client = OpenAICompatibleClient(transport=httpx.MockTransport(handler))
    deltas = [
        delta
        async for delta in client.stream_chat_completion_events(
            base_url="https://models.example/v1",
            api_key="test-key",
            model_id="chat-model",
            messages=[{"role": "user", "content": "Use the tool."}],
            tools=[tool_definition],
        )
    ]

    assert len(deltas) == 2
    assert deltas[0].tool_calls[0].index == 0
    assert deltas[0].tool_calls[0].call_id == "call-1"
    assert deltas[0].tool_calls[0].name == "mcp_echo"
    assert deltas[0].tool_calls[0].arguments == '{"value":'
    assert deltas[1].tool_calls[0].call_id is None
    assert deltas[1].tool_calls[0].name is None
    assert deltas[1].tool_calls[0].arguments == '"hello"}'
    assert deltas[1].finish_reason == "tool_calls"
