import hashlib

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models import AuthSession


async def create_owner(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/setup",
        json={"username": "Owner", "password": "correct horse battery staple"},
    )
    assert response.status_code == 201


async def test_first_access_requires_setup(unauthenticated_api_client) -> None:
    client, _, _ = unauthenticated_api_client

    response = await client.get("/api/auth/status")

    assert response.status_code == 200
    assert response.json() == {
        "setup_required": True,
        "authenticated": False,
        "username": None,
    }


async def test_setup_creates_single_owner_and_authenticated_session(
    unauthenticated_api_client,
) -> None:
    client, _, _ = unauthenticated_api_client

    await create_owner(client)

    status_response = await client.get("/api/auth/status")
    duplicate_response = await client.post(
        "/api/auth/setup",
        json={"username": "another", "password": "another secure password"},
    )

    assert status_response.json() == {
        "setup_required": False,
        "authenticated": True,
        "username": "owner",
    }
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"]["code"] == "setup_complete"


async def test_session_token_is_stored_only_as_a_hash(unauthenticated_api_client) -> None:
    client, _, session_factory = unauthenticated_api_client
    await create_owner(client)
    token = client.cookies.get("aster_session")
    assert token

    async with session_factory() as database:
        auth_session = await database.scalar(select(AuthSession))

    assert auth_session is not None
    assert auth_session.token_hash != token
    assert auth_session.token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()


async def test_private_routes_require_authentication(unauthenticated_api_client) -> None:
    client, _, _ = unauthenticated_api_client
    await create_owner(client)
    client.cookies.clear()

    response = await client.get("/api/persona")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"


async def test_login_and_logout_cycle(unauthenticated_api_client) -> None:
    client, _, _ = unauthenticated_api_client
    await create_owner(client)
    client.cookies.clear()

    wrong = await client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "wrong password"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "OWNER", "password": "correct horse battery staple"},
    )
    authenticated = await client.get("/api/auth/me")
    logout = await client.post("/api/auth/logout")
    logged_out = await client.get("/api/auth/me")

    assert wrong.status_code == 401
    assert login.status_code == 200
    assert authenticated.status_code == 200
    assert authenticated.json()["username"] == "owner"
    assert logout.status_code == 204
    assert logged_out.status_code == 401


async def test_password_change_revokes_other_sessions(unauthenticated_api_client) -> None:
    client, _, _ = unauthenticated_api_client
    await create_owner(client)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as second_client:
        login = await second_client.post(
            "/api/auth/login",
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        assert login.status_code == 200

        changed = await client.put(
            "/api/auth/password",
            json={
                "current_password": "correct horse battery staple",
                "new_password": "a different and secure password",
            },
        )
        first_session = await client.get("/api/auth/me")
        second_session = await second_client.get("/api/auth/me")
        old_login = await second_client.post(
            "/api/auth/login",
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        new_login = await second_client.post(
            "/api/auth/login",
            json={"username": "owner", "password": "a different and secure password"},
        )

    assert changed.status_code == 200
    assert first_session.status_code == 200
    assert second_session.status_code == 401
    assert old_login.status_code == 401
    assert new_login.status_code == 200


async def test_revoke_other_sessions_keeps_current_session(unauthenticated_api_client) -> None:
    client, _, _ = unauthenticated_api_client
    await create_owner(client)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as second_client:
        await second_client.post(
            "/api/auth/login",
            json={"username": "owner", "password": "correct horse battery staple"},
        )

        revoked = await client.delete("/api/auth/sessions")
        first_session = await client.get("/api/auth/me")
        second_session = await second_client.get("/api/auth/me")

    assert revoked.status_code == 200
    assert revoked.json()["revoked_sessions"] == 1
    assert first_session.status_code == 200
    assert second_session.status_code == 401


async def test_login_is_rate_limited(unauthenticated_api_client) -> None:
    client, _, _ = unauthenticated_api_client
    await create_owner(client)
    client.cookies.clear()

    for _ in range(5):
        response = await client.post(
            "/api/auth/login",
            json={"username": "owner", "password": "wrong password"},
        )
        assert response.status_code == 401

    blocked = await client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "wrong password"},
    )

    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1


async def test_cross_origin_mutation_is_rejected(unauthenticated_api_client) -> None:
    client, _, _ = unauthenticated_api_client

    response = await client.post(
        "/api/auth/setup",
        headers={"Origin": "https://evil.example"},
        json={"username": "owner", "password": "correct horse battery staple"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "origin_not_allowed"
