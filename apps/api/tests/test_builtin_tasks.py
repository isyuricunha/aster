from uuid import UUID

from sqlalchemy import func, select

from app.automation_models import Automation, AutomationRun
from app.builtin_tasks import BUILTIN_TASKS, execute_builtin_task
from app.config import settings
from app.dependencies import get_secret_cipher
from app.retrieval_models import Memory


def automation_update_payload(task: dict[str, object]) -> dict[str, object]:
    return {
        "name": task["name"],
        "description": task["description"],
        "instruction": task["instruction"],
        "enabled": task["enabled"],
        "trigger_type": task["trigger_type"],
        "timezone": task["timezone"],
        "schedule": task["schedule"],
        "model_id": task["model_id"],
        "persona_id": task["persona_id"],
        "use_default_persona": False,
        "notify_on_success": task["notify_on_success"],
        "notify_on_failure": task["notify_on_failure"],
        "max_attempts": task["max_attempts"],
        "retry_delay_seconds": task["retry_delay_seconds"],
        "timeout_seconds": task["timeout_seconds"],
        "deliveries": [],
    }


async def test_builtin_tasks_are_seeded_with_stable_defaults(api_client: tuple) -> None:
    client, _, _ = api_client

    response = await client.get("/api/tasks")
    assert response.status_code == 200, response.text
    tasks = response.json()

    assert len(tasks) == len(BUILTIN_TASKS) == 7
    by_key = {item["builtin_key"]: item for item in tasks}
    assert set(by_key) == {item.key for item in BUILTIN_TASKS}

    assert by_key["email_calendar_events"]["schedule"]["display_cron"] == "0 */1 * * *"
    assert by_key["email_summary"]["schedule"]["display_cron"] == "0 */2 * * *"
    assert by_key["email_ai_auto_reply"]["schedule"]["display_cron"] == "0 */2 * * *"
    assert by_key["email_mark_boundaries"]["schedule"]["display_cron"] == "0 */2 * * *"
    assert by_key["email_tags"]["schedule"]["display_cron"] == "0 * * * *"
    assert by_key["memory_tidy"]["schedule"]["display_schedule"] == (
        "Every 5 memories added"
    )

    skills = by_key["skills_audit"]
    assert skills["enabled"] is False
    assert skills["next_run_at"] is None
    assert skills["state"]["availability"] == "requires_skills"


async def test_builtin_tasks_can_be_paused_run_and_cannot_fake_skills(api_client: tuple) -> None:
    client, _, _ = api_client
    tasks = (await client.get("/api/tasks")).json()
    by_key = {item["builtin_key"]: item for item in tasks}

    summary = by_key["email_summary"]
    paused = await client.post(
        f"/api/tasks/{summary['id']}/enabled",
        json={"enabled": False},
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["enabled"] is False
    assert paused.json()["next_run_at"] is None

    activated = await client.post(
        f"/api/tasks/{summary['id']}/enabled",
        json={"enabled": True},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["enabled"] is True
    assert activated.json()["next_run_at"] is not None

    legacy_update = await client.put(
        f"/api/automations/{summary['id']}",
        json=automation_update_payload(summary),
    )
    assert legacy_update.status_code == 409

    legacy_delete = await client.delete(f"/api/automations/{summary['id']}")
    assert legacy_delete.status_code == 409

    memory = by_key["memory_tidy"]
    queued = await client.post(f"/api/tasks/{memory['id']}/run")
    assert queued.status_code == 202, queued.text
    assert queued.json()["status"] == "queued"
    assert queued.json()["automation_name"] == "Memory Tidy"

    skills = by_key["skills_audit"]
    enable_skills = await client.post(
        f"/api/tasks/{skills['id']}/enabled",
        json={"enabled": True},
    )
    assert enable_skills.status_code == 409

    run_skills = await client.post(f"/api/tasks/{skills['id']}/run")
    assert run_skills.status_code == 409

    legacy_run_skills = await client.post(f"/api/automations/{skills['id']}/run")
    assert legacy_run_skills.status_code == 409


async def test_memory_tidy_removes_only_exact_scope_duplicates(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    tasks = (await client.get("/api/tasks")).json()
    memory_task = next(item for item in tasks if item["builtin_key"] == "memory_tidy")
    queued = await client.post(f"/api/tasks/{memory_task['id']}/run")
    assert queued.status_code == 202, queued.text

    async with session_factory() as session:
        session.add_all(
            [
                Memory(content="Keep PostgreSQL backups", category="instruction"),
                Memory(content="  keep postgresql   backups  ", category="other"),
                Memory(content="Use pnpm", category="instruction"),
                Memory(content="Prefer Android", category="preference"),
                Memory(content="Dwarf Fortress is the favorite game", category="preference"),
                Memory(content="The project is named Aster", category="project"),
            ]
        )
        await session.commit()

        automation = await session.get(Automation, UUID(memory_task["id"]))
        run = await session.get(AutomationRun, UUID(queued.json()["id"]))
        assert automation is not None
        assert run is not None

        result = await execute_builtin_task(
            session,
            automation=automation,
            run=run,
            client=fake_client,
            cipher=get_secret_cipher(),
            settings=settings,
        )
        assert result.response == "Removed 1 exact duplicate memory record(s)."
        assert int(await session.scalar(select(func.count(Memory.id))) or 0) == 5

        remaining = list(await session.scalars(select(Memory).order_by(Memory.created_at)))
        assert sum(item.content == "Keep PostgreSQL backups" for item in remaining) == 1
        assert all(item.content.strip() != "keep postgresql   backups" for item in remaining)
