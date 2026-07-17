import base64

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.image_models import ImageModelProfile
from app.models import ModelCacheEntry, ModelEndpoint, ModelPreferences
from app.openai_compatible import ModelEndpointError

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlK7YQAAAAASUVORK5CYII="
)


async def configure_image_model(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    image_role: bool = True,
) -> str:
    async with session_factory() as session:
        endpoint = ModelEndpoint(
            name="Image provider",
            base_url="https://images.example.com/v1",
            enabled=True,
        )
        session.add(endpoint)
        await session.flush()
        model = ModelCacheEntry(
            endpoint_id=endpoint.id,
            model_id="image-model",
            is_manual=True,
            is_available=True,
        )
        session.add(model)
        await session.flush()
        session.add(
            ImageModelProfile(
                model_id=model.id,
                supports_generation=True,
                supports_editing=True,
                supports_multiple_inputs=True,
                supports_masks=True,
                max_input_images=4,
                default_size="1024x1024",
                default_quality="high",
                default_output_format="png",
                default_count=1,
                provider_parameters={"style": "natural"},
            )
        )
        session.add(
            ModelPreferences(
                id=1,
                image_model_id=model.id if image_role else None,
                primary_model_id=None if image_role else model.id,
            )
        )
        await session.commit()
        return str(model.id)


async def upload_png(client, filename: str = "reference.png") -> dict:
    response = await client.post(
        "/api/media-assets/uploads",
        params={"filename": filename},
        headers={"Content-Type": "image/png"},
        content=PNG,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_generation_is_persisted_in_chat_and_gallery(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_image_model(session_factory)
    conversation = (await client.post("/api/conversations", json={})).json()

    generated = await client.post(
        f"/api/conversations/{conversation['id']}/image-operations",
        json={
            "prompt": "A quiet observatory above the clouds",
            "size": "1536x1024",
            "provider_parameters": {"seed": 42},
        },
    )

    assert generated.status_code == 201, generated.text
    operation = generated.json()
    assert operation["status"] == "completed"
    assert operation["operation_type"] == "generation"
    assert operation["revised_prompt"] == "A revised image prompt"
    assert len(operation["outputs"]) == 1
    assert operation["outputs"][0]["media_type"] == "image/png"
    assert operation["parameters"] == {
        "style": "natural",
        "seed": 42,
        "size": "1536x1024",
        "quality": "high",
        "output_format": "png",
        "n": 1,
    }
    assert fake_client.image_client.generate_calls[0]["model_id"] == "image-model"

    detail = (await client.get(f"/api/conversations/{conversation['id']}")).json()
    assert detail["messages"][-1]["content"] == "Generated 1 image."
    assert detail["messages"][-1]["attachments"][0]["attachment_type"] == "output"
    assert detail["messages"][-2]["attachments"] == []

    content = await client.get(operation["outputs"][0]["content_url"])
    assert content.status_code == 200
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.content.startswith(b"\x89PNG")

    gallery = (await client.get("/api/image-gallery")).json()
    assert gallery["total"] == 1
    assert gallery["items"][0]["id"] == operation["id"]

    text_regeneration = await client.post(
        f"/api/conversations/{conversation['id']}/messages/"
        f"{operation['assistant_message_id']}/regenerate"
    )
    assert text_regeneration.status_code == 422
    assert "Start a new image operation" in text_regeneration.text


async def test_primary_model_fallback_requires_declared_image_capability(
    api_client: tuple,
) -> None:
    client, _, session_factory = api_client
    model_id = await configure_image_model(session_factory, image_role=False)
    conversation = (await client.post("/api/conversations", json={})).json()

    response = await client.post(
        f"/api/conversations/{conversation['id']}/image-operations",
        json={"prompt": "A geometric black tower"},
    )

    assert response.status_code == 201
    assert response.json()["model_cache_entry_id"] == model_id


async def test_image_edit_uses_uploaded_inputs_and_mask(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_image_model(session_factory)
    conversation = (await client.post("/api/conversations", json={})).json()
    source = await upload_png(client)
    mask = await upload_png(client, "mask.png")

    edited = await client.post(
        f"/api/conversations/{conversation['id']}/image-operations",
        json={
            "prompt": "Replace the sky with a star field",
            "input_asset_ids": [source["id"]],
            "mask_asset_id": mask["id"],
            "input_fidelity": "high",
        },
    )

    assert edited.status_code == 201, edited.text
    operation = edited.json()
    assert operation["operation_type"] == "edit"
    assert operation["inputs"][0]["id"] == source["id"]
    assert operation["outputs"][0]["source_type"] == "edited"
    call = fake_client.image_client.edit_calls[0]
    assert len(call["images"]) == 1
    assert call["mask"] is not None
    assert call["parameters"]["input_fidelity"] == "high"

    detail = (await client.get(f"/api/conversations/{conversation['id']}")).json()
    assert detail["messages"][-2]["attachments"][0]["id"] == source["id"]
    assert detail["messages"][-1]["attachments"][0]["source_type"] == "edited"


async def test_provider_failure_remains_visible_without_outputs(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_image_model(session_factory)
    conversation = (await client.post("/api/conversations", json={})).json()
    fake_client.image_client.error = ModelEndpointError(
        "upstream_error",
        "The provider failed deliberately.",
        502,
    )

    response = await client.post(
        f"/api/conversations/{conversation['id']}/image-operations",
        json={"prompt": "This operation should fail"},
    )

    assert response.status_code == 502
    gallery = (await client.get("/api/image-gallery")).json()
    assert gallery["total"] == 1
    assert gallery["items"][0]["status"] == "failed"
    assert gallery["items"][0]["outputs"] == []
    assert gallery["items"][0]["error_code"] == "upstream_error"

    detail = (await client.get(f"/api/conversations/{conversation['id']}")).json()
    assert detail["messages"][-1]["status"] == "failed"
    assert detail["messages"][-1]["error_message"] == "The provider failed deliberately."


async def test_deleting_conversation_removes_generated_output(api_client: tuple) -> None:
    client, _, session_factory = api_client
    await configure_image_model(session_factory)
    conversation = (await client.post("/api/conversations", json={})).json()
    operation = (
        await client.post(
            f"/api/conversations/{conversation['id']}/image-operations",
            json={"prompt": "A disposable test image"},
        )
    ).json()
    content_url = operation["outputs"][0]["content_url"]
    assert (await client.get(content_url)).status_code == 200

    deleted = await client.delete(f"/api/conversations/{conversation['id']}")

    assert deleted.status_code == 204
    assert (await client.get(content_url)).status_code == 404
    assert (await client.get("/api/image-gallery")).json()["total"] == 0


async def test_unreferenced_upload_can_be_deleted(api_client: tuple) -> None:
    client, _, _ = api_client
    asset = await upload_png(client)

    deleted = await client.delete(f"/api/media-assets/{asset['id']}")

    assert deleted.status_code == 204
    assert (await client.get(asset["content_url"])).status_code == 404


async def test_image_routes_require_authentication(unauthenticated_api_client: tuple) -> None:
    client, _, _ = unauthenticated_api_client
    assert (await client.get("/api/image-model-profiles")).status_code == 401
    assert (await client.get("/api/image-gallery")).status_code == 401
