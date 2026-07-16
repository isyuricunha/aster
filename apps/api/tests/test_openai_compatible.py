import httpx
import pytest

from app.openai_compatible import ModelEndpointError, OpenAICompatibleClient


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
