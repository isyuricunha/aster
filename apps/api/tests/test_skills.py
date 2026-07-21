import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.automation_models import Automation, AutomationRun
from app.builtin_tasks import builtin_task_ready, execute_builtin_task
from app.config import settings
from app.dependencies import get_secret_cipher
from app.models import ModelCacheEntry, ModelEndpoint, ModelPreferences
from app.skill_models import Skill


def skill_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Release note writer",
        "description": "Write concise release notes from a bounded change list.",
        "instructions": (
            "Given a list of verified product changes, write concise release notes. "
            "Do not invent features, dates, metrics, or compatibility claims."
        ),
        "source_type": "manual",
        "tags": ["release-notes", "writing"],
        "trigger_phrases": ["write release notes", "summarize this changelog"],
        "test_cases": [],
    }
    payload.update(overrides)
    return payload


async def configure_utility(
    session_factory: async_sessionmaker[AsyncSession],
) -> ModelCacheEntry:
    async with session_factory() as session:
        endpoint = ModelEndpoint(
            name="Skill provider",
            base_url="https://example.com/v1",
            enabled=True,
        )
        session.add(endpoint)
        await session.flush()
        model = ModelCacheEntry(
            endpoint_id=endpoint.id,
            model_id="skill-auditor",
            is_manual=True,
            is_available=True,
        )
        session.add(model)
        await session.flush()
        session.add(
            ModelPreferences(
                id=1,
                primary_model_id=model.id,
                utility_model_id=model.id,
            )
        )
        await session.commit()
        return model


def audit_json(
    *,
    verdict: str,
    score: int,
    suggestion: dict[str, object],
    tests_pass: bool,
    duplicate_skill_id: str | None = None,
) -> str:
    tests = [
        {
            "input": "Added export to Markdown.",
            "expected": "Mentions only the Markdown export addition.",
            "passed": tests_pass,
            "reason": "The skill stays within the supplied changes.",
        },
        {
            "input": "Fixed a login crash.",
            "expected": "Mentions only the verified login crash fix.",
            "passed": tests_pass,
            "reason": "No unsupported claims are introduced.",
        },
    ]
    return json.dumps(
        {
            "verdict": verdict,
            "score": score,
            "rationale": "The skill is bounded and testable.",
            "issues": [] if verdict == "pass" else ["Add concrete behavioral tests."],
            "duplicate_skill_id": duplicate_skill_id,
            "suggested_skill": suggestion,
            "tests": tests,
        }
    )


async def test_skill_crud_resets_audit_after_content_changes(api_client: tuple) -> None:
    client, _, session_factory = api_client

    created = await client.post("/api/skills", json=skill_payload())
    assert created.status_code == 201, created.text
    skill = created.json()
    assert skill["status"] == "draft"
    assert skill["audit_status"] == "pending"
    assert skill["content_revision"] == 1

    async with session_factory() as session:
        stored = await session.get(Skill, UUID(skill["id"]))
        assert stored is not None
        stored.audit_status = "passed"
        stored.audit_score = 95
        stored.status = "published"
        stored.audited_revision = stored.content_revision
        await session.commit()

    updated = await client.put(
        f"/api/skills/{skill['id']}",
        json=skill_payload(description="Updated bounded release-note writer."),
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["content_revision"] == 2
    assert body["status"] == "draft"
    assert body["audit_status"] == "pending"
    assert body["audit_score"] is None
    assert body["audited_revision"] is None

    deleted = await client.delete(f"/api/skills/{skill['id']}")
    assert deleted.status_code == 204


async def test_skill_audit_preferences_require_teacher_model(api_client: tuple) -> None:
    client, _, session_factory = api_client

    invalid = await client.put(
        "/api/skill-audit-preferences",
        json={
            "auto_approve_threshold": 90,
            "max_self_edit_attempts": 1,
            "max_skills_per_run": 5,
            "teacher_rewrite_enabled": True,
            "teacher_model_id": None,
        },
    )
    assert invalid.status_code == 422

    model = await configure_utility(session_factory)
    updated = await client.put(
        "/api/skill-audit-preferences",
        json={
            "auto_approve_threshold": 90,
            "max_self_edit_attempts": 1,
            "max_skills_per_run": 5,
            "teacher_rewrite_enabled": True,
            "teacher_model_id": str(model.id),
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["teacher_model_id"] == str(model.id)
    assert updated.json()["teacher_model_name"] == "Skill provider / skill-auditor"


async def test_skills_audit_is_ready_after_five_pending_skills(api_client: tuple) -> None:
    client, _, session_factory = api_client
    tasks = (await client.get("/api/tasks")).json()
    task_json = next(item for item in tasks if item["builtin_key"] == "skills_audit")

    for index in range(4):
        response = await client.post(
            "/api/skills",
            json=skill_payload(name=f"Skill {index}", instructions=f"Bounded instruction {index}."),
        )
        assert response.status_code == 201, response.text

    async with session_factory() as session:
        task = await session.get(Automation, UUID(task_json["id"]))
        assert task is not None
        assert await builtin_task_ready(session, task) is False

    fifth = await client.post(
        "/api/skills",
        json=skill_payload(name="Skill 5", instructions="Fifth bounded instruction."),
    )
    assert fifth.status_code == 201, fifth.text

    async with session_factory() as session:
        task = await session.get(Automation, UUID(task_json["id"]))
        assert task is not None
        assert await builtin_task_ready(session, task) is True


async def test_skill_audit_self_edits_rechecks_and_publishes(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_utility(session_factory)

    created = await client.post("/api/skills", json=skill_payload())
    assert created.status_code == 201, created.text
    skill = created.json()

    suggestion = skill_payload(
        instructions=(
            "Use only the verified change list supplied by the user. Produce a concise heading and "
            "bullets. Never invent features, dates, metrics, migration steps, or compatibility "
            "claims."
        ),
        test_cases=[
            {
                "input": "Added export to Markdown.",
                "expected": "Mentions only the Markdown export addition.",
            },
            {
                "input": "Fixed a login crash.",
                "expected": "Mentions only the verified login crash fix.",
            },
        ],
    )
    fake_client.chat_chunk_rounds = [
        [audit_json(verdict="revise", score=72, suggestion=suggestion, tests_pass=False)],
        [audit_json(verdict="pass", score=94, suggestion=suggestion, tests_pass=True)],
    ]

    queued = await client.post(f"/api/skills/{skill['id']}/audit")
    assert queued.status_code == 202, queued.text
    run_id = UUID(queued.json()["run_id"])

    async with session_factory() as session:
        task = await session.scalar(
            select(Automation).where(Automation.builtin_key == "skills_audit")
        )
        run = await session.get(AutomationRun, run_id)
        assert task is not None
        assert run is not None
        assert run.trigger_payload == {"skill_id": skill["id"]}
        result = await execute_builtin_task(
            session,
            automation=task,
            run=run,
            client=fake_client,
            cipher=get_secret_cipher(),
            settings=settings,
        )
        assert "1 published" in result.response

    refreshed = await client.get(f"/api/skills/{skill['id']}")
    assert refreshed.status_code == 200
    audited = refreshed.json()
    assert audited["status"] == "published"
    assert audited["audit_status"] == "passed"
    assert audited["audit_score"] == 94
    assert audited["content_revision"] == 2
    assert audited["audited_revision"] == 2
    assert len(audited["test_cases"]) == 2
    assert audited["attempt_count"] == 2

    attempts = (await client.get(f"/api/skill-audit-attempts?skill_id={skill['id']}")).json()
    assert [item["stage"] for item in reversed(attempts)] == ["audit", "self_edit"]
    assert fake_client.chat_calls == ["skill-auditor", "skill-auditor"]


async def test_skill_audit_marks_exact_duplicate_without_model_call(api_client: tuple) -> None:
    client, fake_client, session_factory = api_client
    await configure_utility(session_factory)

    original = await client.post(
        "/api/skills",
        json=skill_payload(name="Original release notes"),
    )
    assert original.status_code == 201, original.text
    duplicate = await client.post(
        "/api/skills",
        json=skill_payload(name="Duplicate release notes"),
    )
    assert duplicate.status_code == 201, duplicate.text

    queued = await client.post(f"/api/skills/{duplicate.json()['id']}/audit")
    assert queued.status_code == 202, queued.text

    async with session_factory() as session:
        task = await session.scalar(
            select(Automation).where(Automation.builtin_key == "skills_audit")
        )
        run = await session.get(AutomationRun, UUID(queued.json()["run_id"]))
        assert task is not None
        assert run is not None
        result = await execute_builtin_task(
            session,
            automation=task,
            run=run,
            client=fake_client,
            cipher=get_secret_cipher(),
            settings=settings,
        )
        assert "1 duplicate" in result.response

    audited = (await client.get(f"/api/skills/{duplicate.json()['id']}")).json()
    assert audited["status"] == "draft"
    assert audited["audit_status"] == "duplicate"
    assert audited["duplicate_of_id"] == original.json()["id"]
    assert audited["duplicate_name"] == "Original release notes"
    assert "duplicate" in audited["tags"]
    assert fake_client.chat_calls == []
