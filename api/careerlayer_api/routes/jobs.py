import json
import uuid
from typing import Any

import pymupdf
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from .. import storage
from ..deps import CurrentUser, DbSession
from ..jd_intake import (
    RejectedJob,
    accept_pdf,
    normalize_job_text,
)
from ..models import AuditLog, JobDescription, JobSource, JobState, Requirement
from ..observability import log
from ..queue import enqueue_job_processing
from ..schemas import JobAccepted, JobDescriptionOut, JobSummary, SeverityCounts
from ..settings import get_settings

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


def _safe_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _safe_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return False


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_job(request: Request, user: CurrentUser, session: DbSession) -> JobAccepted:
    """Create a job description from pasted text or an uploaded PDF file."""
    settings = get_settings()
    content_type = request.headers.get("content-type", "")

    title: str | None = None
    company: str | None = None
    location: str | None = None
    raw_text: str | None = None
    is_fixture: bool = False
    file_bytes: bytes | None = None
    filename: str | None = None

    if content_type.startswith("application/json"):
        try:
            body = await request.json()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "invalid_input", "message": "Invalid JSON body."},
            ) from exc
        raw_text = _safe_str(body.get("raw_text"))
        title = _safe_str(body.get("title"))
        company = _safe_str(body.get("company"))
        location = _safe_str(body.get("location"))
        is_fixture = _safe_bool(body.get("is_fixture", False))
    elif content_type.startswith("multipart/form-data"):
        try:
            form = await request.form()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": "invalid_input", "message": "Invalid form data."},
            ) from exc
        title = _safe_str(form.get("title"))
        company = _safe_str(form.get("company"))
        location = _safe_str(form.get("location"))
        raw_text = _safe_str(form.get("raw_text"))
        is_fixture = _safe_bool(form.get("is_fixture", False))
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            file_bytes = await upload.read()
            filename = getattr(upload, "filename", None)
    else:
        # Also support plain text or fallback JSON
        try:
            raw_body = await request.body()
            if raw_body:
                decoded = json.loads(raw_body.decode("utf-8"))
                raw_text = _safe_str(decoded.get("raw_text"))
                title = _safe_str(decoded.get("title"))
                company = _safe_str(decoded.get("company"))
                location = _safe_str(decoded.get("location"))
                is_fixture = _safe_bool(decoded.get("is_fixture", False))
        except Exception:
            pass

    has_text = bool(raw_text)
    has_file = bool(file_bytes)

    if (not has_text and not has_file) or (has_text and has_file):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_input",
                "message": "Provide either raw_text or an uploaded PDF file, not both or neither.",
            },
        )

    # 1. Handle Pasted Text Input
    if has_text:
        assert raw_text is not None
        log("job_intake_pasted_started", user_id=str(user.id))
        try:
            normalized = normalize_job_text(raw_text)
        except RejectedJob as rejected:
            log("job_intake_rejected", user_id=str(user.id), code=rejected.code)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={"code": rejected.code, "message": rejected.message},
            ) from rejected

        # Check deduplication by (user_id, sha256)
        existing = await session.execute(
            select(JobDescription).where(
                JobDescription.user_id == user.id,
                JobDescription.sha256 == normalized.sha256,
            )
        )
        already = existing.scalar_one_or_none()
        if already is not None:
            log(
                "job_intake_deduplicated",
                user_id=str(user.id),
                job_description_id=str(already.id),
            )
            return JobAccepted(
                job_description_id=str(already.id),
                state=already.state,
                source=already.source,
                title=already.title,
                company=already.company,
                sha256=already.sha256,
                duplicate_of_existing=True,
            )

        job = JobDescription(
            user_id=user.id,
            title=title,
            company=company,
            location=location,
            source=JobSource.PASTED,
            raw_text=raw_text,
            normalized_text=normalized.normalized_text,
            sha256=normalized.sha256,
            page_count=None,
            state=JobState.COMPLETED,
            is_fixture=is_fixture,
        )
        session.add(job)
        await session.flush()

        audit = AuditLog(
            user_id=user.id,
            action="job_description_created",
            subject_type="job_description",
            subject_id=str(job.id),
        )
        session.add(audit)
        await session.commit()

        log("job_intake_completed", job_description_id=str(job.id), source="pasted")
        return JobAccepted(
            job_description_id=str(job.id),
            state=job.state,
            source=job.source,
            title=job.title,
            company=job.company,
            sha256=job.sha256,
            duplicate_of_existing=False,
        )

    # 2. Handle Uploaded PDF Input
    assert file_bytes is not None
    log("job_intake_upload_started", user_id=str(user.id), filename=filename)
    try:
        accepted_pdf = accept_pdf(
            file_bytes,
            max_bytes=settings.max_upload_bytes,
            max_pages=settings.max_page_count,
        )
    except RejectedJob as rejected:
        log("job_intake_rejected", user_id=str(user.id), code=rejected.code)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": rejected.code, "message": rejected.message},
        ) from rejected

    # Extract text from PDF for normalization & deduplication check
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        page_texts = [str(doc[page_num].get_text()) for page_num in range(doc.page_count)]
        extracted_raw_text = "\n\n".join(page_texts)
        doc.close()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_pdf",
                "message": "Could not extract text layer from the PDF.",
            },
        ) from exc

    try:
        normalized = normalize_job_text(extracted_raw_text)
    except RejectedJob as rejected:
        log("job_intake_rejected", user_id=str(user.id), code=rejected.code)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": rejected.code, "message": rejected.message},
        ) from rejected

    # Check deduplication
    existing = await session.execute(
        select(JobDescription).where(
            JobDescription.user_id == user.id,
            JobDescription.sha256 == normalized.sha256,
        )
    )
    already = existing.scalar_one_or_none()
    if already is not None:
        log(
            "job_intake_deduplicated",
            user_id=str(user.id),
            job_description_id=str(already.id),
        )
        return JobAccepted(
            job_description_id=str(already.id),
            state=already.state,
            source=already.source,
            title=already.title,
            company=already.company,
            sha256=already.sha256,
            duplicate_of_existing=True,
        )

    job = JobDescription(
        user_id=user.id,
        title=title,
        company=company,
        location=location,
        source=JobSource.UPLOADED,
        raw_text=extracted_raw_text,
        normalized_text=normalized.normalized_text,
        sha256=normalized.sha256,
        page_count=accepted_pdf.page_count,
        state=JobState.QUEUED,
        is_fixture=is_fixture,
    )
    session.add(job)
    await session.flush()

    job.storage_key = storage.job_original_key(str(job.id))
    try:
        storage.put(job.storage_key, file_bytes, "application/pdf")
    except storage.StorageUnavailable as exc:
        log(
            "job_storage_failed",
            user_id=str(user.id),
            job_description_id=str(job.id),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "storage_unavailable",
                "message": "Storage is unavailable.",
            },
        ) from exc

    audit = AuditLog(
        user_id=user.id,
        action="job_description_created",
        subject_type="job_description",
        subject_id=str(job.id),
    )
    session.add(audit)
    await session.commit()

    enqueue_job_processing(str(job.id))
    log(
        "job_intake_queued",
        job_description_id=str(job.id),
        pages=accepted_pdf.page_count,
    )

    return JobAccepted(
        job_description_id=str(job.id),
        state=job.state,
        source=job.source,
        title=job.title,
        company=job.company,
        sha256=job.sha256,
        duplicate_of_existing=False,
    )


@router.get("", response_model=list[JobSummary])
async def list_jobs(user: CurrentUser, session: DbSession) -> list[JobSummary]:
    """List all job descriptions belonging to the authenticated caller."""
    result = await session.execute(
        select(JobDescription)
        .where(JobDescription.user_id == user.id)
        .order_by(JobDescription.created_at.desc())
    )
    jobs = result.scalars().all()
    return [
        JobSummary(
            job_description_id=str(j.id),
            title=j.title,
            company=j.company,
            location=j.location,
            source=j.source,
            state=j.state,
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobDescriptionOut)
async def get_job(job_id: str, user: CurrentUser, session: DbSession) -> JobDescriptionOut:
    """Get detail for a single job description owned by the caller."""
    try:
        parsed_id = uuid.UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Job description not found."},
        ) from exc

    result = await session.execute(
        select(JobDescription).where(
            JobDescription.id == parsed_id, JobDescription.user_id == user.id
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        # Strict security rule: non-owned resource returns 404, never 403
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Job description not found."},
        )

    # Count requirements
    req_count = (
        await session.scalar(
            select(func.count(Requirement.id)).where(Requirement.job_description_id == job.id)
        )
        or 0
    )

    audit = AuditLog(
        user_id=user.id,
        action="job_description_read",
        subject_type="job_description",
        subject_id=str(job.id),
    )
    session.add(audit)
    await session.commit()

    return JobDescriptionOut(
        job_description_id=str(job.id),
        title=job.title,
        company=job.company,
        location=job.location,
        source=job.source,
        state=job.state,
        raw_text=job.raw_text,
        normalized_text=job.normalized_text,
        sha256=job.sha256,
        page_count=job.page_count,
        failure_code=job.failure_code,
        extractor_version=job.extractor_version,
        is_fixture=job.is_fixture,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        requirement_count=req_count,
        findings_by_severity=SeverityCounts(),
    )
