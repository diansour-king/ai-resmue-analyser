import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..deps import CurrentUser, DbSession
from ..llm.prompts import (
    PROMPT_VERSION_RESUME_MATCHING_V1,
    SYSTEM_PROMPT_RESUME_MATCHING_V1,
    ensure_prompt_version_async,
)
from ..models import (
    AuditLog,
    Claim,
    ClaimEvidence,
    ClaimFinding,
    JobDescription,
    JobState,
    MatchRun,
    MatchRunState,
    ProcessingState,
    Requirement,
    Resume,
)
from ..observability import log
from ..queue import enqueue_match_processing
from ..schemas import (
    ClaimEvidenceOut,
    ClaimFindingOut,
    ClaimOut,
    MatchAccepted,
    MatchCreate,
    MatchJobSummary,
    MatchListOut,
    MatchRunOut,
    MatchSummary,
)
from ..settings import get_settings

router = APIRouter(prefix="/v1/matches", tags=["matches"])


def _parse_uuid(val: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(val)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "invalid_input", "message": f"Invalid {field_name} format."},
        ) from exc


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_match(
    payload: MatchCreate, user: CurrentUser, session: DbSession
) -> MatchAccepted:
    """Create or deduplicate a resume-to-job match run and dispatch the matching worker."""
    settings = get_settings()
    resume_id = _parse_uuid(payload.resume_id, "resume_id")
    job_id = _parse_uuid(payload.job_description_id, "job_description_id")

    # 1. Validate Resume ownership and processing readiness
    resume_res = await session.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id)
    )
    resume = resume_res.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resume_not_found", "message": "Resume not found."},
        )

    if resume.state != ProcessingState.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "resume_not_ready",
                "message": "Resume is still processing or has failed.",
            },
        )

    # 2. Validate JobDescription ownership and readiness
    job_res = await session.execute(
        select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user.id)
    )
    job = job_res.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "job_not_found", "message": "Job description not found."},
        )

    if job.state != JobState.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "job_not_ready",
                "message": "Job description is still processing or has failed.",
            },
        )

    # 3. Validate that the job description has extracted requirements
    req_count_res = await session.execute(
        select(func.count())
        .select_from(Requirement)
        .where(Requirement.job_description_id == job.id)
    )
    req_count = req_count_res.scalar() or 0
    if req_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "job_has_no_requirements",
                "message": "Job description has no extracted requirements.",
            },
        )

    # 4. Resolve prompt version for matching
    pv = await ensure_prompt_version_async(
        session,
        name=PROMPT_VERSION_RESUME_MATCHING_V1,
        purpose="matching",
        template=SYSTEM_PROMPT_RESUME_MATCHING_V1,
        model=settings.llm_model,
    )

    scoring_version = "v1"

    # 5. Check for existing MatchRun under unique key
    # (resume_id, job_description_id, prompt_version_id, scoring_version)
    existing_res = await session.execute(
        select(MatchRun).where(
            MatchRun.resume_id == resume.id,
            MatchRun.job_description_id == job.id,
            MatchRun.prompt_version_id == pv.id,
            MatchRun.scoring_version == scoring_version,
        )
    )
    existing = existing_res.scalar_one_or_none()

    if existing is not None:
        if existing.state in (
            MatchRunState.COMPLETED,
            MatchRunState.QUEUED,
            MatchRunState.PROCESSING,
        ):
            log(
                "match_run_deduplicated",
                user_id=str(user.id),
                match_run_id=str(existing.id),
                state=str(existing.state),
            )
            state_str = (
                existing.state.value if hasattr(existing.state, "value") else str(existing.state)
            )
            return MatchAccepted(
                match_run_id=str(existing.id),
                state=state_str,
                resume_id=str(resume.id),
                job_description_id=str(job.id),
                reused=True,
                duplicate_of_existing=True,
            )
        # If failed, re-enqueue for retry
        existing.state = MatchRunState.QUEUED
        existing.failure_code = None
        await session.commit()
        enqueue_match_processing(str(existing.id))
        return MatchAccepted(
            match_run_id=str(existing.id),
            state="queued",
            resume_id=str(resume.id),
            job_description_id=str(job.id),
            reused=True,
            duplicate_of_existing=False,
        )

    # 6. Create new MatchRun
    match_run = MatchRun(
        user_id=user.id,
        resume_id=resume.id,
        job_description_id=job.id,
        state=MatchRunState.QUEUED,
        model=settings.llm_model,
        prompt_version_id=pv.id,
        scoring_version=scoring_version,
    )
    session.add(match_run)
    await session.flush()

    audit = AuditLog(
        user_id=user.id,
        action="match_run_created",
        subject_type="match_run",
        subject_id=str(match_run.id),
    )
    session.add(audit)
    await session.commit()

    enqueue_match_processing(str(match_run.id))
    log(
        "match_run_enqueued",
        user_id=str(user.id),
        match_run_id=str(match_run.id),
        resume_id=str(resume.id),
        job_id=str(job.id),
    )

    return MatchAccepted(
        match_run_id=str(match_run.id),
        state="queued",
        resume_id=str(resume.id),
        job_description_id=str(job.id),
        reused=False,
        duplicate_of_existing=False,
    )


@router.get("", status_code=status.HTTP_200_OK)
async def list_matches(
    user: CurrentUser,
    session: DbSession,
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    resume_id: str | None = None,
    job_description_id: str | None = None,
) -> MatchListOut:
    """List match runs belonging to the authenticated user with deterministic pagination."""
    query = (
        select(MatchRun)
        .options(selectinload(MatchRun.job_description))
        .where(MatchRun.user_id == user.id)
    )

    if cursor:
        cursor_id = _parse_uuid(cursor, "cursor")
        cursor_res = await session.execute(
            select(MatchRun).where(MatchRun.id == cursor_id, MatchRun.user_id == user.id)
        )
        cursor_run = cursor_res.scalar_one_or_none()
        if cursor_run:
            query = query.where(
                (MatchRun.created_at < cursor_run.created_at)
                | ((MatchRun.created_at == cursor_run.created_at) & (MatchRun.id < cursor_run.id))
            )

    if resume_id:
        parsed_resume_id = _parse_uuid(resume_id, "resume_id")
        query = query.where(MatchRun.resume_id == parsed_resume_id)

    if job_description_id:
        parsed_job_id = _parse_uuid(job_description_id, "job_description_id")
        query = query.where(MatchRun.job_description_id == parsed_job_id)

    query = query.order_by(MatchRun.created_at.desc(), MatchRun.id.desc()).limit(limit + 1)

    res = await session.execute(query)
    match_runs = list(res.scalars().all())

    next_cursor = None
    if len(match_runs) > limit:
        match_runs = match_runs[:limit]
        next_cursor = str(match_runs[-1].id)

    items: list[MatchSummary] = []
    for m in match_runs:
        state_str = m.state.value if hasattr(m.state, "value") else str(m.state)
        job_summary = MatchJobSummary(
            job_description_id=str(m.job_description_id),
            title=m.job_description.title if m.job_description else None,
            company=m.job_description.company if m.job_description else None,
            location=m.job_description.location if m.job_description else None,
        )
        items.append(
            MatchSummary(
                match_run_id=str(m.id),
                resume_id=str(m.resume_id),
                job_description_id=str(m.job_description_id),
                state=state_str,
                score=float(m.score) if m.score is not None else None,
                score_if_trusted=(
                    float(m.score_if_trusted) if m.score_if_trusted is not None else None
                ),
                impact_delta=float(m.impact_delta) if m.impact_delta is not None else None,
                requirement_count=m.requirement_count,
                unmet_required_count=m.unmet_required_count,
                job=job_summary,
                created_at=m.created_at.isoformat(),
            )
        )

    return MatchListOut(items=items, next_cursor=next_cursor)


@router.get("/{match_run_id}", status_code=status.HTTP_200_OK)
async def get_match(match_run_id: str, user: CurrentUser, session: DbSession) -> MatchRunOut:
    """Retrieve full match details with structured claims, citations, and scoring breakdown."""
    parsed_match_id = _parse_uuid(match_run_id, "match_run_id")

    query = (
        select(MatchRun)
        .options(
            selectinload(MatchRun.job_description),
            selectinload(MatchRun.prompt_version),
            selectinload(MatchRun.claims).selectinload(Claim.requirement),
            selectinload(MatchRun.claims).selectinload(Claim.primary_evidence_span),
            selectinload(MatchRun.claims)
            .selectinload(Claim.evidence)
            .selectinload(ClaimEvidence.span),
            selectinload(MatchRun.claims)
            .selectinload(Claim.findings)
            .selectinload(ClaimFinding.finding),
        )
        .where(MatchRun.id == parsed_match_id, MatchRun.user_id == user.id)
    )

    res = await session.execute(query)
    match_run = res.scalar_one_or_none()

    if match_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Match run not found."},
        )

    claims_out: list[ClaimOut] = []
    sorted_claims = sorted(
        match_run.claims,
        key=lambda c: (
            c.requirement.ordinal if c.requirement and c.requirement.ordinal is not None else 0
        ),
    )

    for c in sorted_claims:
        req = c.requirement
        primary_span = c.primary_evidence_span
        evidence_detail: ClaimEvidenceOut | None = None
        if primary_span is not None:
            bbox_coords = [
                primary_span.x0,
                primary_span.y0,
                primary_span.x1,
                primary_span.y1,
            ]
            evidence_detail = ClaimEvidenceOut(
                span_id=str(primary_span.id),
                page=primary_span.page,
                quote=primary_span.text,
                bbox=bbox_coords,
            )

        all_spans = [str(ce.span_id) for ce in c.evidence]
        if primary_span and str(primary_span.id) not in all_spans:
            all_spans.insert(0, str(primary_span.id))

        findings_detail: list[ClaimFindingOut] = []
        for cf in c.findings:
            if cf.finding:
                findings_detail.append(
                    ClaimFindingOut(
                        finding_id=str(cf.finding.id),
                        detector_id=cf.finding.detector_id,
                        detector_name=cf.finding.detector_name,
                        severity=cf.finding.severity,
                    )
                )

        claims_out.append(
            ClaimOut(
                claim_id=str(c.id),
                requirement_id=str(c.requirement_id),
                requirement_text=req.text if req else "",
                kind=(
                    req.kind.value
                    if req and hasattr(req.kind, "value")
                    else str(req.kind if req else "hard_skill")
                ),
                necessity=(
                    req.necessity.value
                    if req and hasattr(req.necessity, "value")
                    else str(req.necessity if req else "required")
                ),
                criticality=req.criticality if req else 2,
                weight=float(c.weight_applied),
                met=c.met,
                match_type=(
                    c.match_type.value if hasattr(c.match_type, "value") else str(c.match_type)
                ),
                satisfaction=float(c.satisfaction),
                corroboration=float(c.corroboration),
                integrity_factor=float(c.integrity_factor),
                evidence_quality=float(c.evidence_quality),
                contribution=float(c.contribution),
                confidence=float(c.confidence),
                evidence=evidence_detail,
                all_evidence_spans=all_spans,
                findings=findings_detail,
                rationale=c.rationale,
                adjacency_note=c.adjacency_note,
            )
        )

    state_str = match_run.state.value if hasattr(match_run.state, "value") else str(match_run.state)
    job_summary = MatchJobSummary(
        job_description_id=str(match_run.job_description_id),
        title=match_run.job_description.title if match_run.job_description else None,
        company=match_run.job_description.company if match_run.job_description else None,
        location=match_run.job_description.location if match_run.job_description else None,
    )

    return MatchRunOut(
        match_run_id=str(match_run.id),
        resume_id=str(match_run.resume_id),
        job_description_id=str(match_run.job_description_id),
        state=state_str,
        model=match_run.model,
        scoring_version=match_run.scoring_version,
        prompt_version=match_run.prompt_version.name if match_run.prompt_version else None,
        score=float(match_run.score) if match_run.score is not None else None,
        score_if_trusted=(
            float(match_run.score_if_trusted) if match_run.score_if_trusted is not None else None
        ),
        impact_delta=(
            float(match_run.impact_delta) if match_run.impact_delta is not None else None
        ),
        requirement_count=match_run.requirement_count,
        unmet_required_count=match_run.unmet_required_count,
        job=job_summary,
        claims=claims_out,
        narrative=match_run.narrative,
        failure_code=match_run.failure_code,
        token_cost_usd=(float(match_run.cost_usd) if match_run.cost_usd is not None else None),
        latency_ms=match_run.latency_ms,
        created_at=match_run.created_at.isoformat(),
    )


@router.get("/{match_run_id}/events")
async def match_events(
    match_run_id: str, request: Request, user: CurrentUser, session: DbSession
) -> StreamingResponse:
    """Stream Server-Sent Events (SSE) tracking the match run lifecycle until completion."""
    parsed_match_id = _parse_uuid(match_run_id, "match_run_id")

    # Authorize user owns the match run
    auth_check = await session.execute(
        select(MatchRun).where(MatchRun.id == parsed_match_id, MatchRun.user_id == user.id)
    )
    initial_match = auth_check.scalar_one_or_none()
    if initial_match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Match run not found."},
        )

    session_factory = request.app.state.session_factory

    async def event_generator() -> AsyncIterator[str]:
        # Track emitted stages to avoid redundant duplicate emissions
        last_emitted_state: str | None = None
        iterations = 0
        max_iterations = 600  # 5 minutes max stream duration (0.5s intervals)

        while iterations < max_iterations:
            if await request.is_disconnected():
                break

            async with session_factory() as current_session:
                m_res = await current_session.execute(
                    select(MatchRun).where(MatchRun.id == parsed_match_id)
                )
                m = m_res.scalar_one_or_none()

            if m is None:
                payload = {
                    "stage": "failed",
                    "match_run_id": str(parsed_match_id),
                    "failure_code": "not_found",
                }
                yield f"event: failed\ndata: {json.dumps(payload)}\n\n"
                break

            current_state = m.state.value if hasattr(m.state, "value") else str(m.state)

            if current_state != last_emitted_state:
                last_emitted_state = current_state

                if current_state == MatchRunState.QUEUED.value:
                    payload = {
                        "stage": "queued",
                        "match_run_id": str(parsed_match_id),
                        "state": current_state,
                    }
                    yield f"event: queued\ndata: {json.dumps(payload)}\n\n"

                elif current_state == MatchRunState.PROCESSING.value:
                    payload = {
                        "stage": "scoring",
                        "match_run_id": str(parsed_match_id),
                        "state": current_state,
                    }
                    yield f"event: scoring\ndata: {json.dumps(payload)}\n\n"

                elif current_state == MatchRunState.COMPLETED.value:
                    # Check if canary stage should be signaled prior to complete
                    if m.impact_delta is not None and m.impact_delta > Decimal("0.0"):
                        canary_payload = {
                            "stage": "canary",
                            "match_run_id": str(parsed_match_id),
                            "state": current_state,
                            "impact_delta": float(m.impact_delta),
                        }
                        yield f"event: canary\ndata: {json.dumps(canary_payload)}\n\n"

                    complete_payload = {
                        "stage": "complete",
                        "match_run_id": str(parsed_match_id),
                        "state": current_state,
                        "score": float(m.score) if m.score is not None else None,
                        "score_if_trusted": (
                            float(m.score_if_trusted) if m.score_if_trusted is not None else None
                        ),
                        "impact_delta": (
                            float(m.impact_delta) if m.impact_delta is not None else None
                        ),
                        "unmet_required_count": m.unmet_required_count,
                    }
                    yield f"event: complete\ndata: {json.dumps(complete_payload)}\n\n"
                    break

                elif current_state == MatchRunState.FAILED.value:
                    failed_payload = {
                        "stage": "failed",
                        "match_run_id": str(parsed_match_id),
                        "state": current_state,
                        "failure_code": m.failure_code or "matching_failed",
                    }
                    yield f"event: failed\ndata: {json.dumps(failed_payload)}\n\n"
                    break

            # Send SSE keep-alive comment every 10 iterations (5 seconds)
            if iterations % 10 == 0:
                yield ": keep-alive\n\n"

            iterations += 1
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
