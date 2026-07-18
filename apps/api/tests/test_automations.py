from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.automation_execution import execute_run
from app.automation_models import Automation, AutomationRun, Notification
from app.automation_queue import claim_next_run, enqueue_run
from app.config import settings
from app.models import ModelCacheEntry, ModelEndpoint, ModelPreferences
from app.security import SecretCipher


async def configure_primary(
    session_factory: async_sessionmaker[AsyncSession],
) -> ModelCacheEntry:
    async with session_factory() as session:
        endpoint = ModelEndpoint(
            name="Automation provider",
            base_url="https://example.com/v1",
            enabled=True,
        )
        session.add(endpoint)
        await session.flush()
        model = ModelCacheEntry(
            endpoint_id=endpoint.id,
            model_id="automation-model",
            is_manual=True,
            is_available=True,
        )
        session.add(model)
        await session.flush()
        session.add(ModelPreferences(id=1, primary_model_id=model.id))
        await session.commit()
        return model


def automation_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Daily project brief",
        "description": "A bounded recurring summary.",
        "instruction": "Summarize the project status in three bullets.",
        "enabled": True,
        "trigger_type": "daily",
        "timezone": "America/Sao_Paulo",
        "schedule": {"time": "08:00"},
        "model_id": None,
        "persona_id": None,
        "use_default_persona": False,
        "notify_on_success": True,
        "notify_on_failure": True,
        "max_attempts": 3,
        "retry_delay_seconds": 60,
        "timeout_seconds": 300,
        "deliveries": [],
    }
    payload.update(overrides)
    return payload


async def test_automation_crud_manual_run_and_execution(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_primary(session_factory)

    created = await client.post("/api/automations", json=automation_payload())
    assert created.status_code == 201, created.text
    automation = created.json()
    assert automation["next_run_at"] is not None
    assert automation["webhook_token"] is None

    queued = await client.post(f"/api/automations/{automation['id']}/run")
    assert queued.status_code == 202, queued.text
    run = queued.json()
    assert run["status"] == "queued"

    async with session_factory() as session:
        claimed = await claim_next_run(session, worker_id="test-worker", lease_seconds=120)
    assert claimed is not None
    assert claimed.id.hex == run["id"].replace("-", "")

    fake_client.chat_chunks = ["- API green\n", "- Worker green\n", "- No blockers"]
    await execute_run(
        session_factory,
        run_id=claimed.id,
        worker_id="test-worker",
        client=fake_client,
        cipher=SecretCipher(settings.aster_encryption_key.get_secret_value()),
        settings=settings,
    )

    detail = await client.get(f"/api/automation-runs/{run['id']}")
    assert detail.status_code == 200
    result = detail.json()
    assert result["status"] == "completed"
    assert result["provider_model_id"] == "automation-model"
    assert "Worker green" in result["response"]
    assert result["attempt"] == 1

    notifications = (await client.get("/api/notifications")).json()
    assert notifications["unread_count"] == 1
    assert notifications["items"][0]["level"] == "success"

    updated_payload = automation_payload(
        name="Paused project brief",
        enabled=False,
        trigger_type="interval",
        schedule={"interval_seconds": 3600},
    )
    updated = await client.put(
        f"/api/automations/{automation['id']}",
        json=updated_payload,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["enabled"] is False
    assert updated.json()["next_run_at"] is None


async def test_integration_credentials_are_never_returned(api_client: tuple) -> None:
    client, _, _ = api_client
    created = await client.post(
        "/api/integrations",
        json={
            "name": "Deployment webhook",
            "kind": "webhook",
            "enabled": True,
            "config": {"url": "https://example.com/hooks/aster", "auth_type": "none"},
            "credentials": {
                "Authorization": "Bearer private-token",
                "X-Signature": "private-signature",
            },
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["credential_names"] == ["Authorization", "X-Signature"]
    assert "private-token" not in created.text
    assert "private-signature" not in created.text
    assert "encrypted_credentials" not in created.text

    listed = await client.get("/api/integrations")
    assert "private-token" not in listed.text
    assert "private-signature" not in listed.text


async def test_webhook_trigger_uses_header_secret_and_is_idempotent(
    api_client: tuple,
) -> None:
    client, _, _ = api_client
    created = await client.post(
        "/api/automations",
        json=automation_payload(
            name="Webhook analyzer",
            trigger_type="webhook",
            timezone="UTC",
            schedule={},
        ),
    )
    assert created.status_code == 201, created.text
    automation = created.json()
    token = automation["webhook_token"]
    assert isinstance(token, str) and token
    assert token not in automation["webhook_path"]

    path = f"/api/webhooks/{automation['id']}"
    delivery_headers = {
        "X-Aster-Webhook-Token": token,
        "X-Aster-Delivery": "delivery-123",
    }
    first = await client.post(
        path,
        json={"event": "deployment", "status": "failed"},
        headers=delivery_headers,
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "accepted"
    assert first.json()["run_id"] is not None

    duplicate = await client.post(
        path,
        json={"event": "deployment", "status": "failed"},
        headers=delivery_headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == {"status": "duplicate", "run_id": None}

    missing_secret = await client.post(path, json={"event": "deployment"})
    assert missing_secret.status_code == 422
    wrong_secret = await client.post(
        path,
        json={"event": "deployment"},
        headers={"X-Aster-Webhook-Token": "wrong-secret-value-with-enough-length"},
    )
    assert wrong_secret.status_code == 404

    runs = (await client.get("/api/automation-runs")).json()
    webhook_runs = [item for item in runs if item["automation_id"] == automation["id"]]
    assert len(webhook_runs) == 1
    assert webhook_runs[0]["trigger_payload"]["event"] == "deployment"


async def test_duplicate_occurrence_does_not_rollback_scheduler_state(
    api_client: tuple,
) -> None:
    _, _, session_factory = api_client
    async with session_factory() as session:
        automation = Automation(
            name="Interval test",
            instruction="Return ok.",
            enabled=True,
            trigger_type="interval",
            timezone="UTC",
            schedule={
                "interval_seconds": 3600,
                "anchor_at": datetime.now(UTC).isoformat(),
            },
            next_run_at=datetime.now(UTC),
        )
        session.add(automation)
        await session.commit()
        await session.refresh(automation)

        occurrence = f"schedule:{automation.id}:same"
        first = await enqueue_run(
            session,
            automation,
            trigger_source="schedule",
            occurrence_key=occurrence,
            scheduled_for=datetime.now(UTC),
        )
        assert first is not None
        await session.commit()

        automation.description = "This change must survive the duplicate."
        duplicate = await enqueue_run(
            session,
            automation,
            trigger_source="schedule",
            occurrence_key=occurrence,
            scheduled_for=datetime.now(UTC),
        )
        assert duplicate is None
        await session.commit()

    async with session_factory() as session:
        stored = await session.get(Automation, automation.id)
        assert stored is not None
        assert stored.description == "This change must survive the duplicate."
        count = int(
            await session.scalar(
                select(func.count(AutomationRun.id)).where(
                    AutomationRun.automation_id == automation.id
                )
            )
            or 0
        )
        assert count == 1


async def test_expired_running_run_is_requeued_before_delivery(api_client: tuple) -> None:
    _, _, session_factory = api_client
    async with session_factory() as session:
        automation = Automation(
            name="Lease test",
            instruction="Return ok.",
            enabled=True,
            trigger_type="once",
            timezone="UTC",
            schedule={"run_at": datetime.now(UTC).isoformat()},
        )
        session.add(automation)
        await session.flush()
        run = AutomationRun(
            automation_id=automation.id,
            trigger_source="manual",
            status="running",
            occurrence_key=f"lease:{automation.id}",
            scheduled_for=datetime.now(UTC),
            available_at=datetime.now(UTC),
            attempt=1,
            max_attempts=3,
            retry_delay_seconds=60,
            timeout_seconds=300,
            lease_owner="dead-worker",
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
            trigger_payload={},
            instruction_snapshot=automation.instruction,
        )
        session.add(run)
        await session.commit()
        run_id = run.id

    from app.automation_queue import recover_expired_automation_runs

    async with session_factory() as session:
        assert await recover_expired_automation_runs(session) == 1
        recovered = await session.get(AutomationRun, run_id)
        assert recovered is not None
        assert recovered.status == "queued"
        assert recovered.lease_owner is None
        assert recovered.error_code == "worker_interrupted"

    async with session_factory() as session:
        assert int(await session.scalar(select(func.count(Notification.id))) or 0) == 0
