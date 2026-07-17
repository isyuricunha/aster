import json

import httpx
import pytest

from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient


@pytest.mark.asyncio
async def test_embeddings_preserve_provider_indexes() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url == "https://models.example/v1/embeddings"
        assert payload == {
            "model": "embedding-model",
            "input": ["alpha", "beta"],
            "encoding_format": "float",
        }
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            },
        )

    client = OpenAICompatibleClient(transport=httpx.MockTransport(handler))

    vectors = await client.create_embeddings(
        base_url="https://models.example/v1",
        api_key=None,
        model_id="embedding-model",
        inputs=["alpha", "beta"],
    )

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]


@pytest.mark.asyncio
async def test_embeddings_reject_inconsistent_dimensions() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={
                "data": [
                    {"index": 0, "embedding": [1.0]},
                    {"index": 1, "embedding": [0.0, 1.0]},
                ]
            },
        )
    )
    client = OpenAICompatibleClient(transport=transport)

    with pytest.raises(ModelEndpointError) as raised:
        await client.create_embeddings(
            base_url="https://models.example/v1",
            api_key=None,
            model_id="embedding-model",
            inputs=["alpha", "beta"],
        )

    assert raised.value.code == "invalid_response"
    assert "inconsistent dimensions" in raised.value.message


@pytest.mark.asyncio
async def test_embeddings_hide_upstream_response_bodies() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(401, text="private provider details")
    )
    client = OpenAICompatibleClient(transport=transport)

    with pytest.raises(ModelEndpointError) as raised:
        await client.create_embeddings(
            base_url="https://models.example/v1",
            api_key="bad-key",
            model_id="embedding-model",
            inputs=["alpha"],
        )

    assert raised.value.code == "authentication_failed"
    assert "private provider details" not in raised.value.message
