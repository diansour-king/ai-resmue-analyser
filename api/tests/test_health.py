from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from careerlayer_api.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_liveness_does_not_touch_dependencies(client: AsyncClient) -> None:
    """Liveness must answer while Postgres is down, or a database outage restarts the API."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


async def test_request_id_is_echoed_when_the_caller_supplies_one(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-Id": "bff-42"})

    assert response.headers["x-request-id"] == "bff-42"
    assert response.json()["request_id"] == "bff-42"


async def test_request_id_is_generated_when_absent(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.headers["x-request-id"]


async def test_security_headers_are_present(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    # HSTS is production-only; the test environment is `development`.
    assert "strict-transport-security" not in response.headers


async def test_the_scoring_package_and_httpx_import_in_the_api_process() -> None:
    """B1 regression guard: the API imports the matches router, which imports
    `careerlayer.scoring`; `llm/client.py` calls `httpx` at request time. Both must resolve
    inside whatever environment runs the API, not only on a developer's machine."""
    import httpx  # noqa: F401

    import careerlayer.scoring  # noqa: F401
