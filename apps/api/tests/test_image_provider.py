import base64
import json

import httpx

from app.image_provider import OpenAICompatibleImageClient

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlK7YQAAAAASUVORK5CYII="
)


async def test_generation_omits_edit_only_input_fidelity() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(PNG).decode()}]},
        )

    client = OpenAICompatibleImageClient(
        timeout_seconds=30,
        max_output_bytes=1_000_000,
        max_outputs=4,
        transport=httpx.MockTransport(handler),
    )

    result = await client.generate(
        base_url="https://images.example.com/v1",
        api_key="secret",
        model_id="image-model",
        prompt="A black observatory",
        parameters={
            "size": "1024x1024",
            "quality": "high",
            "input_fidelity": "high",
        },
    )

    assert result[0].data == PNG
    assert captured == {
        "model": "image-model",
        "prompt": "A black observatory",
        "size": "1024x1024",
        "quality": "high",
    }
