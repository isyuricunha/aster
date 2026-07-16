import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_persona_defaults_are_neutral(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]

    response = await client.get("/api/persona")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == ""
    assert payload["instructions"] == ""
    assert payload["enabled"] is False
    assert payload["instruction_role"] == "developer"
    assert payload["created_at"]
    assert payload["updated_at"]


@pytest.mark.asyncio
async def test_persona_update_is_persisted(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    payload = {
        "name": "Personal Assistant",
        "instructions": "Answer in the user's language.",
        "enabled": True,
        "instruction_role": "developer",
    }

    updated = await client.put("/api/persona", json=payload)
    loaded = await client.get("/api/persona")

    assert updated.status_code == 200
    assert loaded.status_code == 200
    assert {key: loaded.json()[key] for key in payload} == payload


@pytest.mark.asyncio
async def test_preview_keeps_persona_and_user_roles_separate(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    await client.put(
        "/api/persona",
        json={
            "name": "Personal Assistant",
            "instructions": "Be warm and direct.",
            "enabled": True,
            "instruction_role": "developer",
        },
    )
    user_message = "  Preserve my spacing and çãracters.  "

    response = await client.post(
        "/api/message-composition/preview",
        json={"user_message": user_message},
    )

    assert response.status_code == 200
    assert response.json()["messages"] == [
        {
            "role": "developer",
            "source": "persona",
            "content": "Your name is Personal Assistant.\n\nBe warm and direct.",
        },
        {
            "role": "user",
            "source": "user",
            "content": user_message,
        },
    ]


@pytest.mark.asyncio
async def test_disabled_persona_is_not_in_preview(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    await client.put(
        "/api/persona",
        json={
            "name": "Personal Assistant",
            "instructions": "Be warm and direct.",
            "enabled": False,
            "instruction_role": "developer",
        },
    )

    response = await client.post(
        "/api/message-composition/preview",
        json={"user_message": "Hello"},
    )

    assert response.json()["messages"] == [
        {"role": "user", "source": "user", "content": "Hello"}
    ]


@pytest.mark.asyncio
async def test_system_role_uses_persona_delimiters(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    await client.put(
        "/api/persona",
        json={
            "name": "",
            "instructions": "Be concise.",
            "enabled": True,
            "instruction_role": "system",
        },
    )

    response = await client.post(
        "/api/message-composition/preview",
        json={"user_message": "Hello"},
    )

    message = response.json()["messages"][0]
    assert message["role"] == "system"
    assert message["source"] == "persona"
    assert message["content"] == (
        "[USER_DEFINED_PERSONA]\nBe concise.\n[/USER_DEFINED_PERSONA]"
    )


@pytest.mark.asyncio
async def test_persona_changes_apply_to_the_next_preview(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    base_payload = {
        "name": "",
        "enabled": True,
        "instruction_role": "developer",
    }
    await client.put(
        "/api/persona",
        json={**base_payload, "instructions": "First version."},
    )
    first = await client.post(
        "/api/message-composition/preview",
        json={"user_message": "Hello"},
    )

    await client.put(
        "/api/persona",
        json={**base_payload, "instructions": "Second version."},
    )
    second = await client.post(
        "/api/message-composition/preview",
        json={"user_message": "Hello"},
    )

    assert first.json()["messages"][0]["content"] == "First version."
    assert second.json()["messages"][0]["content"] == "Second version."
