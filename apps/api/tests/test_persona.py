from httpx import AsyncClient


async def create_persona(
    client: AsyncClient,
    *,
    name: str = "Research Assistant",
    instructions: str = "Be precise.",
    enabled: bool = True,
) -> dict:
    response = await client.post(
        "/api/personas",
        json={
            "name": name,
            "description": "Focused research support.",
            "instructions": instructions,
            "enabled": enabled,
            "instruction_role": "developer",
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_legacy_persona_defaults_are_neutral(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]

    response = await client.get("/api/persona")

    assert response.status_code == 200
    assert response.json()["name"] == ""
    assert response.json()["instructions"] == ""
    assert response.json()["enabled"] is False
    assert response.json()["instruction_role"] == "developer"


async def test_persona_library_creates_default_and_preserves_order(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    created = await create_persona(client)

    personas = (await client.get("/api/personas")).json()
    preferences = (await client.get("/api/persona-preferences")).json()

    assert personas[0]["id"] == created["id"]
    assert personas[0]["is_default"] is True
    assert preferences["default_persona"]["id"] == created["id"]


async def test_persona_duplicate_import_and_default_validation(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    source = await create_persona(client)

    duplicate = await client.post(f"/api/personas/{source['id']}/duplicate")
    assert duplicate.status_code == 201
    assert duplicate.json()["name"] == "Research Assistant copy"
    assert duplicate.json()["is_default"] is False

    imported = await client.post(
        "/api/personas/import",
        json={
            "format": "aster-persona",
            "version": 1,
            "name": "Imported Persona",
            "description": "Imported description.",
            "instructions": "Use imported rules.",
            "enabled": False,
            "instruction_role": "system",
        },
    )
    assert imported.status_code == 201
    assert imported.json()["instruction_role"] == "system"

    disabled_default = await client.put(
        "/api/persona-preferences",
        json={"default_persona_id": imported.json()["id"]},
    )
    assert disabled_default.status_code == 422


async def test_preview_supports_default_specific_and_no_persona(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    persona = await create_persona(client, name="Assistant", instructions="Be direct.")

    default_preview = await client.post(
        "/api/message-composition/preview",
        json={"user_message": "Hello"},
    )
    specific_preview = await client.post(
        "/api/message-composition/preview",
        json={
            "user_message": "Hello",
            "persona_id": persona["id"],
            "use_default_persona": False,
        },
    )
    no_persona_preview = await client.post(
        "/api/message-composition/preview",
        json={"user_message": "Hello", "use_default_persona": False},
    )

    expected_persona = {
        "role": "developer",
        "source": "persona",
        "content": "Your name is Assistant.\n\nBe direct.",
    }
    assert default_preview.json()["messages"][0] == expected_persona
    assert specific_preview.json()["messages"][0] == expected_persona
    assert no_persona_preview.json()["messages"] == [
        {"role": "user", "source": "user", "content": "Hello"}
    ]


async def test_conversation_snapshots_do_not_drift_with_library_changes(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    persona = await create_persona(client, instructions="First version.")
    conversation = (await client.post("/api/conversations", json={})).json()

    assert conversation["persona"]["instructions"] == "First version."
    assert conversation["persona"]["source_persona_id"] == persona["id"]

    updated = await client.put(
        f"/api/personas/{persona['id']}",
        json={
            "name": persona["name"],
            "description": persona["description"],
            "instructions": "Second version.",
            "enabled": True,
            "instruction_role": "developer",
        },
    )
    assert updated.status_code == 200

    unchanged = (await client.get(f"/api/conversations/{conversation['id']}")).json()
    assert unchanged["persona"]["instructions"] == "First version."

    assert (await client.delete(f"/api/personas/{persona['id']}")).status_code == 204
    preserved = (await client.get(f"/api/conversations/{conversation['id']}")).json()
    assert preserved["persona"]["name"] == "Research Assistant"
    assert preserved["persona"]["instructions"] == "First version."
    assert preserved["persona"]["source_persona_id"] is None


async def test_conversation_persona_can_be_replaced_or_cleared(api_client: tuple) -> None:
    client: AsyncClient = api_client[0]
    first = await create_persona(client, name="First", instructions="First rules.")
    second = await create_persona(client, name="Second", instructions="Second rules.")
    conversation = (await client.post("/api/conversations", json={})).json()

    replaced = await client.patch(
        f"/api/conversations/{conversation['id']}",
        json={"persona_id": second["id"]},
    )
    assert replaced.status_code == 200
    assert replaced.json()["persona"]["name"] == "Second"
    assert replaced.json()["persona"]["instructions"] == "Second rules."

    cleared = await client.patch(
        f"/api/conversations/{conversation['id']}",
        json={"persona_id": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["persona"] is None

    assert first["id"] != second["id"]


async def test_legacy_persona_update_remains_compatible(api_client: tuple) -> None:
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
    assert {key: loaded.json()[key] for key in payload} == payload
