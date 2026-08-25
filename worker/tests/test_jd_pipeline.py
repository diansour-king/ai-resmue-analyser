import uuid

import pymupdf

from careerlayer_api import storage
from careerlayer_api.models import JobDescription, JobSource, JobState, User
from careerlayer_worker.db import session_scope
from careerlayer_worker.jd_pipeline import process_job_description


def _build_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data: bytes = bytes(doc.tobytes())
    doc.close()
    return data


def test_uploaded_pdf_job_processes_to_completion() -> None:
    user_id = uuid.uuid4()
    with session_scope() as session:
        user = User(id=user_id, email=f"jd-worker-{user_id.hex[:8]}@example.com")
        session.add(user)
        session.flush()

        job_id = uuid.uuid4()
        job = JobDescription(
            id=job_id,
            user_id=user.id,
            title="Senior DevOps Engineer",
            company="CloudWorks",
            source=JobSource.UPLOADED,
            raw_text="Initial raw placeholder",
            normalized_text="Initial raw placeholder",
            sha256="temp-sha",
            storage_key=storage.job_original_key(str(job_id)),
            state=JobState.QUEUED,
        )
        session.add(job)

    pdf_bytes = _build_pdf(
        "Senior DevOps Engineer. Required: Kubernetes, Terraform, AWS, and Prometheus."
    )
    assert job.storage_key is not None
    storage.put(job.storage_key, pdf_bytes, "application/pdf")

    result = process_job_description(str(job_id))
    assert result == "completed"

    with session_scope() as session:
        refreshed = session.get(JobDescription, job_id)
        assert refreshed is not None
        assert refreshed.state == JobState.COMPLETED
        assert refreshed.failure_code is None
        assert refreshed.page_count == 1
        assert "Kubernetes" in refreshed.normalized_text
        assert "Terraform" in refreshed.normalized_text
        assert refreshed.sha256 is not None


def test_a_missing_job_is_not_an_error() -> None:
    missing_id = str(uuid.uuid4())
    result = process_job_description(missing_id)
    assert result == "missing"


def test_reprocessing_job_is_idempotent() -> None:
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    with session_scope() as session:
        user = User(id=user_id, email=f"jd-worker-idem-{user_id.hex[:8]}@example.com")
        session.add(user)
        session.flush()

        job = JobDescription(
            id=job_id,
            user_id=user.id,
            title="Backend Lead",
            source=JobSource.PASTED,
            raw_text="Backend Lead requirements.",
            normalized_text="Backend Lead requirements.",
            sha256="backend-sha",
            state=JobState.COMPLETED,
        )
        session.add(job)

    result = process_job_description(str(job_id))
    assert result == "completed"
