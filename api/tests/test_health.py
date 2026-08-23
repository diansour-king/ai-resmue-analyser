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
