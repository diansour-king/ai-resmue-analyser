import os
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "packages/integrity/tests/fixtures"

_TEST_DB = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://careerlayer:careerlayer@127.0.0.1:5432/careerlayer_test",
)

# Settings are read once and cached, so the environment has to be right before anything
# imports the application.
os.environ.setdefault("DATABASE_URL", _TEST_DB)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/1")
os.environ.setdefault("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
os.environ.setdefault("S3_BUCKET", "careerlayer-test")
os.environ.setdefault("ENVIRONMENT", "development")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from careerlayer_api import storage  # noqa: E402
from careerlayer_api.db import Base  # noqa: E402
from careerlayer_api.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def schema() -> Iterator[None]:
    """Create the schema directly from the models rather than by running migrations.

    The migration is verified separately against a real Postgres; making every test run
    depend on the whole migration chain would make an unrelated failure look like a broken
    test suite.
    """
    import asyncio

    async def build() -> None:
        engine = create_async_engine(_TEST_DB)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(build())
    yield


@pytest.fixture(scope="session", autouse=True)
def bucket(schema: None) -> None:
    storage.ensure_bucket()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
    ):
        yield http


@pytest.fixture(autouse=True)
def no_real_queue(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record what would have been enqueued instead of requiring a live worker.

    The worker's own tests run the pipeline directly. What matters here is that the request
    hands off rather than doing the work, and that is exactly what this records.
    """
    enqueued: list[str] = []

    def fake_enqueue(resume_id: str) -> str:
        enqueued.append(resume_id)
        return f"job-{resume_id}"

    monkeypatch.setattr("careerlayer_api.routes.resumes.enqueue_processing", fake_enqueue)
    return enqueued


@pytest.fixture
async def signed_in(client: AsyncClient) -> str:
    """Complete the magic-link flow and leave the session cookie on the client."""
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    issued = await client.post("/v1/auth/signup", json={"email": email})
    token = issued.json()["login_url"].split("token=")[1]
    await client.post("/v1/auth/verify", json={"token": token})
    return email


def read_fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()
