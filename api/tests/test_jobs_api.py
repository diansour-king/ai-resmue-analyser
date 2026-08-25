import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from careerlayer_api.jd_intake import (
    MAX_JD_TOKENS,
    RejectedJob,
    normalize_job_text,
)
from careerlayer_api.models import AuditLog, JobSource, JobState
from careerlayer_api.settings import get_settings


def _make_pdf_bytes(text: str) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data: bytes = bytes(doc.tobytes())
    doc.close()
    return data


def test_normalization_and_offsets() -> None:
    # 1. NFKC folding (e.g. ligature ﬁ -> fi)
    raw = "Senior ﬁntech engineer with 5+ years experience."
    norm = normalize_job_text(raw)
    assert "fintech" in norm.normalized_text
    assert norm.sha256 == normalize_job_text(norm.normalized_text).sha256

    # 2. Zero-width and bidi control stripping
    raw_with_zw = "Senior\u200b Python\u200c Developer\u202e"
    norm_zw = normalize_job_text(raw_with_zw)
    assert norm_zw.zero_width_count == 2
    assert norm_zw.bidi_count == 1
    assert norm_zw.normalized_text == "Senior Python Developer"

    # 3. Line endings & collapsing 3+ blank lines to 2
    raw_lines = "Title\r\n\r\n\r\n\r\n\r\nResponsibilities:\n- Python\n\n\n\n- FastAPI"
    norm_lines = normalize_job_text(raw_lines)
    assert "\r" not in norm_lines.normalized_text
    assert "\n\n\n" not in norm_lines.normalized_text
    assert "Title\n\nResponsibilities:\n- Python\n\n- FastAPI" in norm_lines.normalized_text

    # 4. Boilerplate span marking without modifying offsets
    raw_with_boilerplate = (
        "Senior Backend Engineer\n\n"
        "Requirements:\n- Python\n- PostgreSQL\n\n"
        "Equal Opportunity Employer:\n"
        "We do not discriminate based on race, gender, or religion.\n\n"
        "Benefits:\n- Health, Dental, Vision\n- 401(k) matching\n- Unlimited PTO"
    )
    norm_bp = normalize_job_text(raw_with_boilerplate)
    assert len(norm_bp.boilerplate_spans) >= 2
    for span in norm_bp.boilerplate_spans:
        substring = norm_bp.normalized_text[span.start : span.end]
        assert len(substring) > 0

    # 5. Empty rejection
    with pytest.raises(RejectedJob) as exc_info:
        normalize_job_text("   \n\n  \t  ")
    assert exc_info.value.code == "invalid_input"

    # 6. Oversized token limit rejection
    huge_text = "word " * (MAX_JD_TOKENS + 500)
    with pytest.raises(RejectedJob) as exc_info:
        normalize_job_text(huge_text)
    assert exc_info.value.code == "token_limit_exceeded"


@pytest.mark.asyncio
async def test_pasted_job_creation_and_deduplication(client: AsyncClient, signed_in: str) -> None:
    payload = {
        "title": "Staff Backend Engineer",
        "company": "TechCorp",
        "location": "Remote",
        "raw_text": "We are seeking a Staff Backend Engineer with 7+ years of Python.",
    }

    # 1. Create pasted job
    resp = await client.post("/v1/jobs", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data["duplicate_of_existing"] is False
    assert data["state"] == JobState.COMPLETED
    assert data["source"] == JobSource.PASTED
    assert data["title"] == "Staff Backend Engineer"
    assert data["company"] == "TechCorp"
    job_id = data["job_description_id"]

    # 2. Duplicate submission by the same user returns existing job
    dup_resp = await client.post("/v1/jobs", json=payload)
    assert dup_resp.status_code == 202
    dup_data = dup_resp.json()
    assert dup_data["duplicate_of_existing"] is True
    assert dup_data["job_description_id"] == job_id
    assert dup_data["sha256"] == data["sha256"]

    # 3. Verify audit log was recorded in db
    engine = create_async_engine(get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as s:
        audit_rows = (
            (
                await s.execute(
                    select(AuditLog).where(
                        AuditLog.subject_id == job_id,
                        AuditLog.action == "job_description_created",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(audit_rows) >= 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_pdf_job_upload_and_deduplication(
    client: AsyncClient, signed_in: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued: list[str] = []

    def fake_enqueue_job(j_id: str) -> str:
        enqueued.append(j_id)
        return f"job-{j_id}"

    monkeypatch.setattr("careerlayer_api.routes.jobs.enqueue_job_processing", fake_enqueue_job)

    pdf_content = _make_pdf_bytes("Staff Data Engineer at Acme. 5+ years Kafka and PySpark.")
    files = {"file": ("job.pdf", io.BytesIO(pdf_content), "application/pdf")}
    data = {"title": "Staff Data Engineer", "company": "Acme"}

    # 1. Upload PDF
    resp = await client.post("/v1/jobs", files=files, data=data)
    assert resp.status_code == 202
    res_data = resp.json()
    assert res_data["duplicate_of_existing"] is False
    assert res_data["source"] == JobSource.UPLOADED
    assert res_data["state"] == JobState.QUEUED
    job_id = res_data["job_description_id"]
    assert len(enqueued) == 1

    # 2. Duplicate PDF upload returns existing job and does not re-enqueue
    files_dup = {"file": ("job.pdf", io.BytesIO(pdf_content), "application/pdf")}
    dup_resp = await client.post("/v1/jobs", files=files_dup, data=data)
    assert dup_resp.status_code == 202
    dup_data = dup_resp.json()
    assert dup_data["duplicate_of_existing"] is True
    assert dup_data["job_description_id"] == job_id
    assert len(enqueued) == 1


@pytest.mark.asyncio
async def test_job_list_and_detail(client: AsyncClient, signed_in: str) -> None:
    # Create two jobs
    await client.post(
        "/v1/jobs",
        json={"title": "Role A", "company": "Co A", "raw_text": "Role A requirements: Python."},
    )
    await client.post(
        "/v1/jobs",
        json={"title": "Role B", "company": "Co B", "raw_text": "Role B requirements: Go."},
    )

    # 1. List jobs
    list_resp = await client.get("/v1/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    assert len(jobs) >= 2
    job_ids = [j["job_description_id"] for j in jobs]

    # 2. Get detail
    detail_resp = await client.get(f"/v1/jobs/{job_ids[0]}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["job_description_id"] == job_ids[0]
    assert "raw_text" in detail
    assert "normalized_text" in detail
    assert "sha256" in detail
    assert detail["requirement_count"] == 0


@pytest.mark.asyncio
async def test_job_authorization_and_404_isolation(client: AsyncClient, signed_in: str) -> None:
    # 1. Create job with User A
    resp = await client.post(
        "/v1/jobs",
        json={"title": "Private Role", "raw_text": "Private JD content."},
    )
    job_id = resp.json()["job_description_id"]

    # 2. Log in as a second user
    login_resp = await client.post(
        "/v1/auth/signup", json={"email": f"user2-{uuid.uuid4().hex[:6]}@example.com"}
    )
    token = login_resp.json()["login_url"].split("token=")[1]
    await client.post("/v1/auth/verify", json={"token": token})

    # User B accessing User A's JD must get 404 (never 403)
    other_user_resp = await client.get(f"/v1/jobs/{job_id}")
    assert other_user_resp.status_code == 404
    assert other_user_resp.json()["error"]["code"] == "not_found"

    # Non-existent job ID returns 404
    missing_resp = await client.get(f"/v1/jobs/{uuid.uuid4()}")
    assert missing_resp.status_code == 404


@pytest.mark.asyncio
async def test_input_validation_errors(client: AsyncClient, signed_in: str) -> None:
    # 1. Both raw_text and file provided -> 422
    pdf_bytes = _make_pdf_bytes("Test")
    resp = await client.post(
        "/v1/jobs",
        files={"file": ("job.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"raw_text": "Also raw text"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_input"

    # 2. Neither provided -> 422
    resp_empty = await client.post("/v1/jobs", json={})
    assert resp_empty.status_code == 422
    assert resp_empty.json()["error"]["code"] == "invalid_input"

    # 3. Invalid / corrupt PDF -> 422
    corrupt_resp = await client.post(
        "/v1/jobs",
        files={"file": ("corrupt.pdf", io.BytesIO(b"not a pdf"), "application/pdf")},
    )
    assert corrupt_resp.status_code == 422
    assert corrupt_resp.json()["error"]["code"] == "invalid_pdf"
