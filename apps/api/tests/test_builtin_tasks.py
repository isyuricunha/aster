from app.builtin_tasks import BUILTIN_TASKS


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
