import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "packages/integrity/tests/fixtures"

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://careerlayer:careerlayer@127.0.0.1:5432/careerlayer_test",
)
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/1")
os.environ.setdefault("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
os.environ.setdefault("S3_BUCKET", "careerlayer-test")
os.environ.setdefault("ENVIRONMENT", "development")

from careerlayer_api import storage  # noqa: E402
from careerlayer_api.models import ProcessingState, Resume, User  # noqa: E402
from careerlayer_worker.db import session_scope  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def bucket() -> None:
    storage.ensure_bucket()


@pytest.fixture
def uploaded() -> Iterator[Callable[[str], str]]:
    """Put a real fixture PDF through the upload half by hand, then hand back the id.

    The worker's contract starts at a stored PDF and a queued row. Building that directly
    keeps these tests about the pipeline rather than about HTTP.
    """
    created: list[uuid.UUID] = []

    def make(fixture_name: str) -> str:
        content = (FIXTURES / fixture_name).read_bytes()
        with session_scope() as session:
            user = User(email=f"worker-{uuid.uuid4().hex[:8]}@example.com")
            session.add(user)
            session.flush()
            resume = Resume(
                user_id=user.id,
                filename=fixture_name,
                storage_key="",
                sha256=uuid.uuid4().hex * 2,
                byte_size=len(content),
                state=ProcessingState.QUEUED,
            )
            session.add(resume)
            session.flush()
            resume.storage_key = storage.original_key(str(resume.id))
            storage.put(resume.storage_key, content, "application/pdf")
            created.append(resume.id)
            return str(resume.id)

    yield make
