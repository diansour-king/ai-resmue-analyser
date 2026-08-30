import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from careerlayer_api.db import utcnow
from careerlayer_api.main import app
from careerlayer_api.models import LoginToken, User
from careerlayer_api.security import new_token
from careerlayer_api.settings import get_settings


async def test_signup_issues_a_link_and_verifying_it_starts_a_session(
    client: AsyncClient,
) -> None:
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"

    issued = await client.post("/v1/auth/signup", json={"email": email, "display_name": "Alex"})
    assert issued.status_code == 202
    assert issued.json()["sent"] is True
    assert "token=" in issued.json()["login_url"]
    token = issued.json()["login_url"].split("token=")[1]

    verified = await client.post("/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200
    assert verified.json()["email"] == email
    assert verified.json()["display_name"] == "Alex"
    assert verified.json()["onboarded"] is False

    me = await client.get("/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Alex"
    assert me.json()["email"] == email


async def test_login_for_existing_user_issues_link(client: AsyncClient) -> None:
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/v1/auth/signup", json={"email": email, "display_name": "Sam"})

    login_resp = await client.post("/v1/auth/login", json={"email": email})
    assert login_resp.status_code == 202
    assert login_resp.json()["sent"] is True
    assert "token=" in login_resp.json()["login_url"]

    token = login_resp.json()["login_url"].split("token=")[1]
    verified = await client.post("/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200
    assert verified.json()["email"] == email


async def test_login_does_not_reveal_whether_an_address_is_registered(
    client: AsyncClient,
) -> None:
    unknown = await client.post("/v1/auth/login", json={"email": "nobody@example.com"})

    assert unknown.status_code == 202
    assert unknown.json()["sent"] is True
    assert unknown.json()["login_url"] is None


async def test_a_link_cannot_be_used_twice(client: AsyncClient) -> None:
    """One-time really means once. A link may sit in an inbox or a proxy log forever."""
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    issued = await client.post("/v1/auth/signup", json={"email": email})
    token = issued.json()["login_url"].split("token=")[1]

    assert (await client.post("/v1/auth/verify", json={"token": token})).status_code == 200
    replay = await client.post("/v1/auth/verify", json={"token": token})

    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "invalid_link"


async def test_expired_token_is_rejected(client: AsyncClient) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    secret, token_hash = new_token()
    async with session_maker() as session:
        user = User(email=f"expired-{uuid.uuid4().hex[:8]}@example.com", display_name="Old")
        session.add(user)
        await session.flush()

        expired_token = LoginToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=utcnow() - timedelta(minutes=5),
        )
        session.add(expired_token)
        await session.commit()
    await engine.dispose()

    response = await client.post("/v1/auth/verify", json={"token": secret})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_link"


async def test_malformed_or_empty_token_is_rejected(client: AsyncClient) -> None:
    # Non-existent token
    fake_token = "completely-invalid-random-token-that-does-not-exist"
    resp = await client.post("/v1/auth/verify", json={"token": fake_token})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_link"

    # Whitespace only
    resp_ws = await client.post("/v1/auth/verify", json={"token": "   "})
    assert resp_ws.status_code in (400, 422)

    # Empty string
    resp_empty = await client.post("/v1/auth/verify", json={"token": ""})
    assert resp_empty.status_code in (400, 422)


async def test_session_cookie_attributes(client: AsyncClient) -> None:
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    issued = await client.post("/v1/auth/signup", json={"email": email})
    token = issued.json()["login_url"].split("token=")[1]

    verified = await client.post("/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200

    set_cookie = verified.headers.get("set-cookie", "")
    cookie_lower = set_cookie.lower()
    assert "careerlayer_session=" in set_cookie
    assert "httponly" in cookie_lower
    assert "samesite=lax" in cookie_lower
    assert "path=/" in cookie_lower
    assert "max-age=" in cookie_lower
    # Development runs over plain http, so the cookie cannot be Secure by default.
    assert "secure" not in cookie_lower


async def test_cookie_secure_override_is_independent_of_environment(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An HTTPS deployment can keep `environment=development` for the returned link
    and still set `COOKIE_SECURE=true` so the session cookie carries Secure."""
    settings = get_settings()
    monkeypatch.setattr(settings, "cookie_secure", True)

    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    issued = await client.post("/v1/auth/signup", json={"email": email})
    token = issued.json()["login_url"].split("token=")[1]
    verified = await client.post("/v1/auth/verify", json={"token": token})

    assert "secure" in verified.headers.get("set-cookie", "").lower()


async def test_production_environment_does_not_expose_login_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "production")

    email = f"prod-user-{uuid.uuid4().hex[:8]}@example.com"
    # Signup in production
    signup_resp = await client.post(
        "/v1/auth/signup",
        json={"email": email, "display_name": "Prod"},
    )
    assert signup_resp.status_code == 202
    assert signup_resp.json()["sent"] is True
    assert signup_resp.json()["login_url"] is None

    # Login in production
    login_resp = await client.post("/v1/auth/login", json={"email": email})
    assert login_resp.status_code == 202
    assert login_resp.json()["sent"] is True
    assert login_resp.json()["login_url"] is None


async def test_signed_out_requests_are_refused(client: AsyncClient) -> None:
    response = await client.get("/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_logout_revokes_the_session(client: AsyncClient, signed_in: str) -> None:
    assert (await client.get("/v1/auth/me")).status_code == 200

    logout_resp = await client.post("/v1/auth/logout")
    assert logout_resp.status_code == 204

    # The cookie should be deleted / cleared
    assert (await client.get("/v1/auth/me")).status_code == 401


async def test_onboarding_records_a_name(client: AsyncClient, signed_in: str) -> None:
    before = await client.get("/v1/auth/me")
    assert before.json()["onboarded"] is False

    after = await client.post("/v1/auth/onboarding", json={"display_name": "Bikash"})

    assert after.status_code == 200
    assert after.json()["display_name"] == "Bikash"
    assert after.json()["onboarded"] is True


async def test_every_error_has_one_shape(client: AsyncClient) -> None:
    """The frontend builds one error component, so the envelope cannot vary by route."""
    body = (await client.get("/v1/auth/me")).json()

    assert set(body) == {"error", "request_id"}
    assert set(body["error"]) >= {"code", "message"}


async def test_authenticated_user_cannot_access_other_user_data(client: AsyncClient) -> None:
    """Strict tenant isolation: accessing another user's resource returns 404, never 403."""
    # User A creates a job
    email_a = f"user-a-{uuid.uuid4().hex[:8]}@example.com"
    issued_a = await client.post("/v1/auth/signup", json={"email": email_a})
    token_a = issued_a.json()["login_url"].split("token=")[1]
    await client.post("/v1/auth/verify", json={"token": token_a})

    job_resp = await client.post(
        "/v1/jobs",
        json={
            "title": "Backend Lead",
            "company": "Acme Corp",
            "raw_text": "Requirements: Python, Postgres, FastAPI.",
        },
    )
    assert job_resp.status_code == 202
    job_id = job_resp.json()["job_description_id"]

    # User B logs in on a new client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client_b:
        email_b = f"user-b-{uuid.uuid4().hex[:8]}@example.com"
        issued_b = await client_b.post("/v1/auth/signup", json={"email": email_b})
        token_b = issued_b.json()["login_url"].split("token=")[1]
        await client_b.post("/v1/auth/verify", json={"token": token_b})

        # User B tries to get User A's job
        get_resp = await client_b.get(f"/v1/jobs/{job_id}")
        assert get_resp.status_code == 404
        assert get_resp.json()["error"]["code"] == "not_found"
