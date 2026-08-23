import uuid

from httpx import AsyncClient


async def test_signup_issues_a_link_and_verifying_it_starts_a_session(
    client: AsyncClient,
) -> None:
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"

    issued = await client.post("/v1/auth/signup", json={"email": email, "display_name": "Alex"})
    assert issued.status_code == 202
    token = issued.json()["login_url"].split("token=")[1]

    verified = await client.post("/v1/auth/verify", json={"token": token})
    assert verified.status_code == 200
    assert verified.json()["email"] == email

    me = await client.get("/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Alex"


async def test_a_link_cannot_be_used_twice(client: AsyncClient) -> None:
    """One-time really means once. A link may sit in an inbox or a proxy log forever."""
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    issued = await client.post("/v1/auth/signup", json={"email": email})
    token = issued.json()["login_url"].split("token=")[1]

    assert (await client.post("/v1/auth/verify", json={"token": token})).status_code == 200
    replay = await client.post("/v1/auth/verify", json={"token": token})

    assert replay.status_code == 400
    assert replay.json()["error"]["code"] == "invalid_link"


async def test_login_does_not_reveal_whether_an_address_is_registered(
    client: AsyncClient,
) -> None:
    unknown = await client.post("/v1/auth/login", json={"email": "nobody@example.com"})

    assert unknown.status_code == 202
    assert unknown.json()["sent"] is True
    assert unknown.json()["login_url"] is None


async def test_signed_out_requests_are_refused(client: AsyncClient) -> None:
    response = await client.get("/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_logout_revokes_the_session(client: AsyncClient, signed_in: str) -> None:
    assert (await client.get("/v1/auth/me")).status_code == 200

    await client.post("/v1/auth/logout")

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
