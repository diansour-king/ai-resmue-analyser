import uuid

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from .. import storage
from ..deps import CurrentUser, DbSession
from ..models import Finding, ProcessingState, Resume, ResumePage, ResumeSkill, TextSpan
from ..observability import log
from ..pdf_intake import RejectedUpload, accept
from ..queue import enqueue_processing
from ..schemas import (
    BBox,
    FindingOut,
    PageInfo,
    ResumeOut,
    ResumeSummary,
    SeverityCounts,
    SkillEvidenceOut,
    SkillOut,
    UploadAccepted,
)
from ..settings import get_settings

router = APIRouter(prefix="/v1/resumes", tags=["resumes"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload(
    user: CurrentUser, session: DbSession, file: UploadFile = File(...)
) -> UploadAccepted:
    settings = get_settings()
    log("upload_started", user_id=str(user.id), filename=_safe_name(file.filename))
    content = await file.read()

    try:
        accepted = accept(
            content, max_bytes=settings.max_upload_bytes, max_pages=settings.max_page_count
        )
    except RejectedUpload as rejected:
        log("upload_rejected", user_id=str(user.id), code=rejected.code)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": rejected.code, "message": rejected.message},
        ) from rejected

    existing = await session.execute(
        select(Resume).where(Resume.user_id == user.id, Resume.sha256 == accepted.sha256)
    )
    already = existing.scalar_one_or_none()
    if already is not None:
        # Byte-identical re-upload. Rendering and OCR are the expensive part of this system
        # and the answer cannot have changed, so the existing analysis is returned instead.
        log("upload_deduplicated", user_id=str(user.id), resume_id=str(already.id))
        return UploadAccepted(
            resume_id=str(already.id),
            state=already.state,
            filename=already.filename,
            page_count=already.page_count or accepted.page_count,
            duplicate_of_existing=True,
        )

    resume = Resume(
        user_id=user.id,
        filename=_safe_name(file.filename),
        storage_key="",
        sha256=accepted.sha256,
        byte_size=accepted.byte_size,
        page_count=accepted.page_count,
        state=ProcessingState.UPLOADED,
    )
    session.add(resume)
    await session.flush()

    resume.storage_key = storage.original_key(str(resume.id))
    try:
        storage.put(resume.storage_key, content, "application/pdf")
    except storage.StorageUnavailable as exc:
        log("upload_storage_failed", user_id=str(user.id), resume_id=str(resume.id))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "storage_unavailable", "message": "Storage is unavailable."},
        ) from exc

    resume.state = ProcessingState.QUEUED
    await session.commit()
    enqueue_processing(str(resume.id))
    log("upload_completed", resume_id=str(resume.id), pages=accepted.page_count)

    return UploadAccepted(
        resume_id=str(resume.id),
        state=resume.state,
        filename=resume.filename,
        page_count=accepted.page_count,
        duplicate_of_existing=False,
    )


@router.get("")
async def list_resumes(user: CurrentUser, session: DbSession) -> list[ResumeSummary]:
    result = await session.execute(
        select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
    )
    return [
        ResumeSummary(
            resume_id=str(row.id),
            filename=row.filename,
            state=row.state,
            page_count=row.page_count,
            created_at=row.created_at.isoformat(),
        )
        for row in result.scalars()
    ]


@router.get("/{resume_id}")
async def get_resume(resume_id: uuid.UUID, user: CurrentUser, session: DbSession) -> ResumeOut:
    resume = await _owned_resume(session, resume_id, user.id)

    pages = list(
        (
            await session.execute(
                select(ResumePage)
                .where(ResumePage.resume_id == resume.id)
                .order_by(ResumePage.page_number)
            )
        ).scalars()
    )
    counts = await session.execute(
        select(Finding.severity, func.count())
        .where(Finding.resume_id == resume.id)
        .group_by(Finding.severity)
    )
    tally: dict[str, int] = {}
    for severity, total in counts.all():
        tally[severity] = total
    by_severity = SeverityCounts(**tally)
    skill_count = await session.scalar(
        select(func.count()).select_from(ResumeSkill).where(ResumeSkill.resume_id == resume.id)
    )
    page_list = [
        PageInfo(
            page_number=page.page_number,
            width_pt=page.width_pt,
            height_pt=page.height_pt,
            rotation=page.rotation,
            render_width_px=page.render_width_px,
            render_height_px=page.render_height_px,
            render_dpi=page.render_dpi,
            render_available=bool(page.render_key),
        )
        for page in pages
    ]

    return ResumeOut(
        resume_id=str(resume.id),
        filename=resume.filename,
        state=resume.state,
        page_count=resume.page_count,
        byte_size=resume.byte_size,
        failure_code=resume.failure_code,
        created_at=resume.created_at.isoformat(),
        pages=page_list,
        findings_by_severity=by_severity,
        skill_count=skill_count or 0,
        evidence_available=any(page.render_key for page in pages),
    )


@router.get("/{resume_id}/findings")
async def get_findings(
    resume_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> list[FindingOut]:
    await _owned_resume(session, resume_id, user.id)
    result = await session.execute(
        select(Finding)
        .where(Finding.resume_id == resume_id)
        .order_by(Finding.page, Finding.y0, Finding.detector_id)
    )
    return [
        FindingOut(
            finding_id=str(row.id),
            detector_id=row.detector_id,
            detector_name=row.detector_name,
            severity=row.severity,
            confidence=row.confidence,
            page=row.page,
            bbox=BBox(x0=row.x0, y0=row.y0, x1=row.x1, y1=row.y1),
            excerpt=row.excerpt,
            rationale=row.rationale,
        )
        for row in result.scalars()
    ]


@router.get("/{resume_id}/skills")
async def get_skills(resume_id: uuid.UUID, user: CurrentUser, session: DbSession) -> list[SkillOut]:
    await _owned_resume(session, resume_id, user.id)
    result = await session.execute(
        select(ResumeSkill)
        .where(ResumeSkill.resume_id == resume_id)
        .options(selectinload(ResumeSkill.evidence))
        .order_by(ResumeSkill.confidence.desc(), ResumeSkill.canonical_name)
    )
    skills = list(result.scalars())
    span_ids = [link.span_id for skill in skills for link in skill.evidence]
    spans = (
        {
            span.id: span
            for span in (
                await session.execute(select(TextSpan).where(TextSpan.id.in_(span_ids)))
            ).scalars()
        }
        if span_ids
        else {}
    )

    return [
        SkillOut(
            skill_id=str(skill.id),
            canonical_name=skill.canonical_name,
            confidence=skill.confidence,
            support_count=skill.support_count,
            flagged_support_count=skill.flagged_support_count,
            source=skill.source,
            evidence=[
                SkillEvidenceOut(
                    span_id=str(span.id),
                    page=span.page,
                    bbox=BBox(x0=span.x0, y0=span.y0, x1=span.x1, y1=span.y1),
                    text=span.text,
                )
                for link in skill.evidence
                if (span := spans.get(link.span_id)) is not None
            ],
        )
        for skill in skills
    ]


@router.get("/{resume_id}/pages/{page_number}")
async def get_page_render(
    resume_id: uuid.UUID, page_number: int, user: CurrentUser, session: DbSession
) -> Response:
    """Stream the rendered page through the API.

    Never a presigned URL. A presigned URL is a credential the browser can keep and forward,
    and whether someone may look at a resume has to stay a decision this service makes on
    every single request.
    """
    await _owned_resume(session, resume_id, user.id)
    page = (
        await session.execute(
            select(ResumePage).where(
                ResumePage.resume_id == resume_id, ResumePage.page_number == page_number
            )
        )
    ).scalar_one_or_none()
    if page is None or not page.render_key:
        raise _not_found("That page has not been rendered.")

    try:
        chunks = storage.stream(page.render_key)
    except storage.StorageUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "storage_unavailable", "message": "Storage is unavailable."},
        ) from exc
    return StreamingResponse(
        chunks,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=3600"},
    )


async def _owned_resume(session: DbSession, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume:
    """Fetch a resume, or 404 if it is not this user's.

    404 rather than 403 on purpose: distinguishing "does not exist" from "not yours" tells a
    stranger which resume ids are real.
    """
    resume = await session.get(Resume, resume_id)
    if resume is None or resume.user_id != user_id:
        raise _not_found("No such resume.")
    return resume


def _not_found(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "not_found", "message": message},
    )


def _safe_name(filename: str | None) -> str:
    """Keep the base name only. An uploaded name is an attacker-controlled string."""
    if not filename:
        return "resume.pdf"
    return filename.replace("\\", "/").rsplit("/", 1)[-1][:255]
