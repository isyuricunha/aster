from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.conversation_titles import fallback_title, normalize_generated_title
from app.models import ModelCacheEntry, ModelEndpoint, ModelPreferences
from app.openai_compatible import ModelEndpointError


async def configure_title_models(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        primary_endpoint = ModelEndpoint(
            name="Primary endpoint",
            base_url="https://primary.example/v1",
            enabled=True,
        )
        utility_endpoint = ModelEndpoint(
            name="Utility endpoint",
            base_url="https://utility.example/v1",
            enabled=True,
        )
        session.add_all([primary_endpoint, utility_endpoint])
        await session.flush()
        primary = ModelCacheEntry(
            endpoint_id=primary_endpoint.id,
            model_id="primary-model",
            is_manual=True,
            is_available=True,
        )
        utility = ModelCacheEntry(
            endpoint_id=utility_endpoint.id,
            model_id="utility-model",
            is_manual=True,
            is_available=True,
        )
        session.add_all([primary, utility])
        await session.flush()
        session.add(
            ModelPreferences(
                id=1,
                primary_model_id=primary.id,
                utility_model_id=utility.id,
            )
        )
        await session.commit()


async def test_utility_model_generates_first_conversation_title(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_title_models(session_factory)
    fake_client.chat_chunks_by_model["utility-model"] = [
        'Título: "Utility gera títulos"'
    ]
    fake_client.chat_chunks_by_model["primary-model"] = ["Resposta principal"]

    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Explique como o modelo Utility deve gerar títulos."},
    )

    assert response.status_code == 200
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["title"] == "Utility gera títulos"
    assert detail["messages"][-1]["content"] == "Resposta principal"
    assert fake_client.chat_calls == ["utility-model", "primary-model"]


async def test_title_failure_keeps_local_fallback(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_title_models(session_factory)
    fake_client.chat_errors_by_model["utility-model"] = ModelEndpointError(
        "connection_error",
        "Utility unavailable.",
    )
    fake_client.chat_chunks_by_model["primary-model"] = ["Resposta principal"]
    content = "Converse sobre uma falha temporária do modelo Utility."

    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": content},
    )

    assert response.status_code == 200
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["title"] == fallback_title(content)
    assert detail["messages"][-1]["content"] == "Resposta principal"
    assert fake_client.chat_calls == ["utility-model", "primary-model"]


async def test_manual_title_is_not_replaced(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_title_models(session_factory)
    fake_client.chat_chunks_by_model["primary-model"] = ["Resposta principal"]

    conversation_id = (
        await client.post("/api/conversations", json={"title": "Título manual"})
    ).json()["id"]
    response = await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Esta mensagem não deve trocar o título manual."},
    )

    assert response.status_code == 200
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert detail["title"] == "Título manual"
    assert fake_client.chat_calls == ["primary-model"]


async def test_manual_rename_stops_future_title_regeneration(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_title_models(session_factory)
    fake_client.chat_chunks_by_model["utility-model"] = ["Título automático"]
    fake_client.chat_chunks_by_model["primary-model"] = ["Primeira resposta"]

    conversation_id = (await client.post("/api/conversations", json={})).json()["id"]
    await client.post(
        f"/api/conversations/{conversation_id}/messages/stream",
        json={"content": "Primeira solicitação"},
    )
    detail = (await client.get(f"/api/conversations/{conversation_id}")).json()
    first_user_id = detail["messages"][0]["id"]

    renamed = await client.patch(
        f"/api/conversations/{conversation_id}",
        json={"title": "Meu título manual"},
    )
    assert renamed.status_code == 200

    fake_client.chat_chunks_by_model["utility-model"] = ["Não deve ser usado"]
    fake_client.chat_chunks_by_model["primary-model"] = ["Resposta editada"]
    await client.post(
        f"/api/conversations/{conversation_id}/messages/{first_user_id}/edit-and-resend",
        json={"content": "Solicitação editada"},
    )

    updated = (await client.get(f"/api/conversations/{conversation_id}")).json()
    assert updated["title"] == "Meu título manual"
    assert fake_client.chat_calls == ["utility-model", "primary-model", "primary-model"]


def test_generated_title_normalization() -> None:
    assert normalize_generated_title('```text\nTítulo: "Resumo do projeto"\n```') == (
        "Resumo do projeto"
    )
