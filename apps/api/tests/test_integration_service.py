from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest

from app.automation_models import IntegrationConnection
from app.integration_service import (
    decrypt_credentials,
    deliver_calendar_event,
    deliver_email,
    deliver_webhook,
    encrypt_credentials,
    validate_integration_config,
)
from app.security import SecretCipher


@pytest.fixture
def cipher() -> SecretCipher:
    return SecretCipher("tests-only-encryption-key-with-32-characters")


def test_credentials_are_encrypted_and_round_trip(cipher: SecretCipher) -> None:
    credentials = {
        "username": "owner",
        "password": "private-password",
        "Authorization": "Bearer private-token",
    }
    encrypted = encrypt_credentials(cipher, credentials)
    assert encrypted is not None
    assert "private-password" not in encrypted
    assert "private-token" not in encrypted
    assert decrypt_credentials(cipher, encrypted) == credentials


def test_integration_configuration_is_normalized() -> None:
    smtp = validate_integration_config(
        "smtp",
        {
            "host": " smtp.example.com ",
            "port": 587,
            "security": "starttls",
            "from_address": "aster@example.com",
        },
    )
    assert smtp["host"] == "smtp.example.com"

    caldav = validate_integration_config(
        "caldav",
        {
            "calendar_url": "https://calendar.example.com/user/events/",
            "auth_type": "basic",
        },
    )
    assert caldav["calendar_url"] == "https://calendar.example.com/user/events"

    webhook = validate_integration_config(
        "webhook",
        {"url": "https://hooks.example.com/aster/"},
    )
    assert webhook["url"] == "https://hooks.example.com/aster"


async def test_email_delivery_uses_decrypted_credentials(
    monkeypatch: pytest.MonkeyPatch,
    cipher: SecretCipher,
) -> None:
    captured: dict[str, Any] = {}

    def fake_send(
        config: dict[str, object],
        credentials: dict[str, str],
        *,
        recipients: list[str],
        subject: str,
        body: str,
        headers: dict[str, str],
    ) -> None:
        captured.update(
            config=config,
            credentials=credentials,
            recipients=recipients,
            subject=subject,
            body=body,
            headers=headers,
        )

    monkeypatch.setattr("app.integration_service._send_email", fake_send)
    integration = IntegrationConnection(
        name="Mail",
        kind="smtp",
        enabled=True,
        config={
            "host": "smtp.example.com",
            "port": 587,
            "security": "starttls",
            "from_address": "aster@example.com",
        },
        encrypted_credentials=encrypt_credentials(
            cipher,
            {"username": "owner", "password": "private-password"},
        ),
        credential_names=["password", "username"],
    )

    result = await deliver_email(
        integration,
        cipher=cipher,
        recipients=["one@example.com", "two@example.com"],
        subject="Daily brief",
        body="Everything is green.",
    )

    assert result.destination == "one@example.com, two@example.com"
    assert captured["credentials"] == {
        "username": "owner",
        "password": "private-password",
    }
    assert captured["subject"] == "Daily brief"
    assert captured["body"] == "Everything is green."
    assert captured["headers"] == {}


class FakeHttpClient:
    requests: list[dict[str, Any]] = []

    def __init__(self, **_: object) -> None:
        pass

    async def __aenter__(self) -> "FakeHttpClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        headers: dict[str, str],
    ) -> httpx.Response:
        self.requests.append(
            {"method": "POST", "url": url, "json": json, "headers": headers}
        )
        return httpx.Response(202, request=httpx.Request("POST", url))

    async def put(
        self,
        url: str,
        *,
        content: bytes,
        headers: dict[str, str],
        auth: object,
    ) -> httpx.Response:
        self.requests.append(
            {
                "method": "PUT",
                "url": url,
                "content": content,
                "headers": headers,
                "auth": auth,
            }
        )
        return httpx.Response(201, request=httpx.Request("PUT", url))


async def test_outbound_webhook_sends_structured_payload_and_secret_headers(
    monkeypatch: pytest.MonkeyPatch,
    cipher: SecretCipher,
) -> None:
    FakeHttpClient.requests = []
    monkeypatch.setattr("app.integration_service.httpx.AsyncClient", FakeHttpClient)
    integration = IntegrationConnection(
        name="Webhook",
        kind="webhook",
        enabled=True,
        config={"url": "https://hooks.example.com/aster", "auth_type": "none"},
        encrypted_credentials=encrypt_credentials(
            cipher,
            {
                "Authorization": "Bearer private-token",
                "X-Signature": "private-signature",
            },
        ),
        credential_names=["Authorization", "X-Signature"],
    )

    payload = {"type": "aster.automation.completed", "run_id": "run-123"}
    result = await deliver_webhook(
        integration,
        cipher=cipher,
        payload=payload,
        timeout_seconds=30,
    )

    assert result.destination == "https://hooks.example.com/aster"
    request = FakeHttpClient.requests[0]
    assert request["method"] == "POST"
    assert request["json"] == payload
    assert request["headers"] == {
        "Authorization": "Bearer private-token",
        "X-Signature": "private-signature",
    }


async def test_caldav_delivery_creates_a_stable_icalendar_event(
    monkeypatch: pytest.MonkeyPatch,
    cipher: SecretCipher,
) -> None:
    FakeHttpClient.requests = []
    monkeypatch.setattr("app.integration_service.httpx.AsyncClient", FakeHttpClient)
    integration = IntegrationConnection(
        name="Calendar",
        kind="caldav",
        enabled=True,
        config={
            "calendar_url": "https://calendar.example.com/user/events",
            "auth_type": "basic",
        },
        encrypted_credentials=encrypt_credentials(
            cipher,
            {"username": "owner", "password": "private-password"},
        ),
        credential_names=["password", "username"],
    )
    run_id = uuid4()

    result = await deliver_calendar_event(
        integration,
        cipher=cipher,
        uid=run_id,
        summary="Project brief",
        description="Everything is green.",
        start=datetime(2026, 7, 20, 11, tzinfo=UTC),
        duration_minutes=30,
        timeout_seconds=30,
    )

    request = FakeHttpClient.requests[0]
    assert request["method"] == "PUT"
    assert request["url"] == f"https://calendar.example.com/user/events/{run_id}.ics"
    assert request["headers"]["If-None-Match"] == "*"
    content = request["content"].decode("utf-8")
    assert f"UID:{run_id}@aster" in content
    assert "SUMMARY:Project brief" in content
    assert "DESCRIPTION:Everything is green." in content
    assert "DTSTART:20260720T110000Z" in content
    assert result.destination == request["url"]
