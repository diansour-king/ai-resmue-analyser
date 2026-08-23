import uuid
from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from careerlayer_api.models import (
    AuditLog,
    Claim,
    ClaimEvidence,
    ClaimFinding,
    Extraction,
    Finding,
    JobDescription,
    JobSource,
    LLMCall,
    MatchRun,
    MatchRunState,
    MatchType,
    PromptVersion,
    Requirement,
    RequirementKind,
    RequirementNecessity,
    Resume,
    TextSpan,
    User,
)
from careerlayer_api.settings import get_settings


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(get_settings().database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_is_fixture_defaults_and_explicit(session: AsyncSession) -> None:
    user = User(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    await session.commit()

    resume_default = Resume(
        user_id=user.id,
        filename="resume.pdf",
        storage_key="k1",
        sha256="sha1",
        byte_size=1024,
    )
    resume_fixture = Resume(
        user_id=user.id,
        filename="fixture.pdf",
        storage_key="k2",
        sha256="sha2",
        byte_size=1024,
        is_fixture=True,
    )
    job_default = JobDescription(
        user_id=user.id,
        source=JobSource.PASTED,
        raw_text="Job text",
        normalized_text="Job text",
        sha256="jdsha1",
    )
    job_fixture = JobDescription(
        user_id=user.id,
        source=JobSource.PASTED,
        raw_text="Job text 2",
        normalized_text="Job text 2",
        sha256="jdsha2",
        is_fixture=True,
    )

    session.add_all([resume_default, resume_fixture, job_default, job_fixture])
    await session.commit()

    resumes = (
        (
            await session.execute(
                select(Resume).where(Resume.id.in_([resume_default.id, resume_fixture.id]))
            )
        )
        .scalars()
        .all()
    )
    res_map = {r.id: r for r in resumes}
    assert res_map[resume_default.id].is_fixture is False
    assert res_map[resume_fixture.id].is_fixture is True

    jobs = (
        (
            await session.execute(
                select(JobDescription).where(
                    JobDescription.id.in_([job_default.id, job_fixture.id])
                )
            )
        )
        .scalars()
        .all()
    )
    job_map = {j.id: j for j in jobs}
    assert job_map[job_default.id].is_fixture is False
    assert job_map[job_fixture.id].is_fixture is True


@pytest.mark.asyncio
async def test_job_description_user_sha256_uniqueness(session: AsyncSession) -> None:
    user = User(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    await session.commit()

    jd1 = JobDescription(
        user_id=user.id,
        source=JobSource.PASTED,
        raw_text="Senior Python Engineer",
        normalized_text="Senior Python Engineer",
        sha256="same-sha256",
    )
    session.add(jd1)
    await session.commit()

    jd2 = JobDescription(
        user_id=user.id,
        source=JobSource.PASTED,
        raw_text="Duplicate Senior Python Engineer",
        normalized_text="Duplicate Senior Python Engineer",
        sha256="same-sha256",
    )
    session.add(jd2)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_requirements_and_job_description_relation(session: AsyncSession) -> None:
    user = User(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    await session.commit()

    jd = JobDescription(
        user_id=user.id,
        title="Backend Engineer",
        company="Acme Corp",
        location="Remote",
        source=JobSource.PASTED,
        raw_text="5+ years Python required. Kafka preferred.",
        normalized_text="5+ years Python required. Kafka preferred.",
        sha256=uuid.uuid4().hex,
    )
    session.add(jd)
    await session.commit()

    req1 = Requirement(
        job_description_id=jd.id,
        ordinal=1,
        text="5+ years Python in production",
        kind=RequirementKind.HARD_SKILL,
        necessity=RequirementNecessity.REQUIRED,
        criticality=3,
        weight=Decimal("3.0000"),
        evidence_start=0,
        evidence_end=23,
        evidence_quote="5+ years Python required",
    )
    req2 = Requirement(
        job_description_id=jd.id,
        ordinal=2,
        text="Kafka or event streaming",
        kind=RequirementKind.HARD_SKILL,
        necessity=RequirementNecessity.PREFERRED,
        criticality=2,
        weight=Decimal("0.8000"),
        evidence_start=25,
        evidence_end=40,
        evidence_quote="Kafka preferred",
    )
    session.add_all([req1, req2])
    await session.commit()

    # Verify duplicate ordinal constraint
    dup_req = Requirement(
        job_description_id=jd.id,
        ordinal=1,
        text="Duplicate ordinal",
        kind=RequirementKind.EXPERIENCE,
        necessity=RequirementNecessity.REQUIRED,
        criticality=1,
        weight=Decimal("1.0000"),
        evidence_start=0,
        evidence_end=5,
        evidence_quote="5+",
    )
    session.add(dup_req)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_match_run_and_claim_precision_and_constraints(session: AsyncSession) -> None:
    user = User(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    await session.commit()

    resume = Resume(
        user_id=user.id,
        filename="resume.pdf",
        storage_key="resumes/test.pdf",
        sha256=uuid.uuid4().hex,
        byte_size=2048,
    )
    jd = JobDescription(
        user_id=user.id,
        source=JobSource.PASTED,
        raw_text="Python",
        normalized_text="Python",
        sha256=uuid.uuid4().hex,
    )
    pv = PromptVersion(
        name=f"matching-v{uuid.uuid4().hex[:6]}",
        purpose="matching",
        template="system prompt",
        template_sha256="sha256-prompt",
        model="claude-sonnet-5",
    )
    session.add_all([resume, jd, pv])
    await session.commit()

    extraction = Extraction(
        resume_id=resume.id,
        method="fitz",
        page_count=1,
        duration_ms=15,
    )
    session.add(extraction)
    await session.commit()

    span1 = TextSpan(
        extraction_id=extraction.id,
        page=1,
        x0=72.0,
        y0=100.0,
        x1=300.0,
        y1=112.0,
        text="5 years of Python engineering",
        font="Helvetica",
        font_size=10.0,
        colour="#000000",
        render_mode=0,
        opacity=1.0,
        seqno=1,
        char_start=0,
        char_end=28,
    )
    span2 = TextSpan(
        extraction_id=extraction.id,
        page=1,
        x0=72.0,
        y0=120.0,
        x1=300.0,
        y1=132.0,
        text="Built streaming pipelines with Redis Streams",
        font="Helvetica",
        font_size=10.0,
        colour="#000000",
        render_mode=0,
        opacity=1.0,
        seqno=2,
        char_start=29,
        char_end=72,
    )
    finding = Finding(
        resume_id=resume.id,
        detector_id="D1",
        detector_name="invisible_render_mode",
        severity="high",
        confidence=1.0,
        page=1,
        x0=72.0,
        y0=100.0,
        x1=300.0,
        y1=112.0,
        excerpt="5 years of Python engineering",
        rationale="Render mode 3 used",
    )
    req1 = Requirement(
        job_description_id=jd.id,
        ordinal=1,
        text="Python proficiency",
        kind=RequirementKind.HARD_SKILL,
        necessity=RequirementNecessity.REQUIRED,
        criticality=3,
        weight=Decimal("3.0000"),
        evidence_start=0,
        evidence_end=6,
        evidence_quote="Python",
    )
    session.add_all([span1, span2, finding, req1])
    await session.commit()

    match_run = MatchRun(
        user_id=user.id,
        resume_id=resume.id,
        job_description_id=jd.id,
        state=MatchRunState.COMPLETED,
        model="claude-sonnet-5",
        prompt_version_id=pv.id,
        scoring_version="v1.0",
        score=Decimal("60.60"),
        score_if_trusted=Decimal("82.00"),
        impact_delta=Decimal("21.40"),
        requirement_count=6,
        unmet_required_count=1,
        input_tokens=4500,
        output_tokens=1200,
        cost_usd=Decimal("0.0345"),
        latency_ms=1250,
        narrative="1 of 4 required requirements unmet.",
    )
    session.add(match_run)
    await session.commit()

    match_run_id = match_run.id
    req1_id = req1.id
    span1_id = span1.id
    span2_id = span2.id
    finding_id = finding.id
    user_id = user.id
    resume_id = resume.id
    jd_id = jd.id
    pv_id = pv.id

    # Check dedup uniqueness constraint on match_runs
    dup_run = MatchRun(
        user_id=user_id,
        resume_id=resume_id,
        job_description_id=jd_id,
        model="claude-sonnet-5",
        prompt_version_id=pv_id,
        scoring_version="v1.0",
    )
    session.add(dup_run)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    # Check constraint: met=true without primary_evidence_span_id must fail
    invalid_claim = Claim(
        match_run_id=match_run_id,
        requirement_id=req1_id,
        met=True,
        match_type=MatchType.DIRECT,
        satisfaction=Decimal("1.0000"),
        corroboration=Decimal("1.0000"),
        integrity_factor=Decimal("0.0000"),
        evidence_quality=Decimal("0.0000"),
        weight_applied=Decimal("3.0000"),
        contribution=Decimal("0.0000"),
        confidence=Decimal("0.9500"),
        # Violates CHECK (met = false OR primary_evidence_span_id IS NOT NULL)
        primary_evidence_span_id=None,
    )
    session.add(invalid_claim)
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()

    # Valid claim with primary evidence
    valid_claim = Claim(
        match_run_id=match_run_id,
        requirement_id=req1_id,
        met=True,
        match_type=MatchType.DIRECT,
        satisfaction=Decimal("1.0000"),
        corroboration=Decimal("0.8000"),
        integrity_factor=Decimal("0.0000"),
        evidence_quality=Decimal("0.0000"),
        weight_applied=Decimal("3.0000"),
        contribution=Decimal("0.0000"),
        confidence=Decimal("0.9500"),
        primary_evidence_span_id=span1_id,
        rationale="Requirement found in hidden text",
    )
    session.add(valid_claim)
    await session.commit()
    valid_claim_id = valid_claim.id

    # Add multiple corroborating evidence spans and findings
    claim_ev1 = ClaimEvidence(claim_id=valid_claim_id, span_id=span1_id)
    claim_ev2 = ClaimEvidence(claim_id=valid_claim_id, span_id=span2_id)
    claim_find1 = ClaimFinding(claim_id=valid_claim_id, finding_id=finding_id)
    session.add_all([claim_ev1, claim_ev2, claim_find1])
    await session.commit()

    # Verify query and exact numeric precision
    stored_run = (
        await session.execute(select(MatchRun).where(MatchRun.id == match_run_id))
    ).scalar_one()
    assert stored_run.score == Decimal("60.60")
    assert stored_run.score_if_trusted == Decimal("82.00")
    assert stored_run.impact_delta == Decimal("21.40")
    assert stored_run.cost_usd == Decimal("0.0345")

    stored_claim = (
        await session.execute(
            select(Claim)
            .options(selectinload(Claim.evidence), selectinload(Claim.findings))
            .where(Claim.id == valid_claim_id)
        )
    ).scalar_one()
    assert stored_claim.weight_applied == Decimal("3.0000")
    assert stored_claim.corroboration == Decimal("0.8000")
    assert len(stored_claim.evidence) == 2
    assert len(stored_claim.findings) == 1


@pytest.mark.asyncio
async def test_llm_calls_and_audit_log(session: AsyncSession) -> None:
    user = User(email=f"user-{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    await session.commit()

    user_id = user.id
    llm_call = LLMCall(
        user_id=user_id,
        purpose="matching",
        model="claude-sonnet-5",
        input_tokens=2500,
        output_tokens=1500,
        cache_read_tokens=2000,
        cache_write_tokens=0,
        cost_usd=Decimal("0.0345"),
        latency_ms=850,
        outcome="success",
        stop_reason="end_turn",
        attempt=1,
    )
    audit = AuditLog(
        user_id=user_id,
        action="match_run_created",
        subject_type="match_run",
        subject_id=uuid.uuid4().hex,
    )
    session.add_all([llm_call, audit])
    await session.commit()

    llm_call_id = llm_call.id
    audit_id = audit.id

    # Verify user deletion sets user_id to NULL in PostgreSQL ondelete=SET NULL
    await session.delete(user)
    await session.commit()
    session.expire_all()

    refreshed_call = (
        await session.execute(select(LLMCall).where(LLMCall.id == llm_call_id))
    ).scalar_one()
    assert refreshed_call.user_id is None

    refreshed_audit = (
        await session.execute(select(AuditLog).where(AuditLog.id == audit_id))
    ).scalar_one()
    assert refreshed_audit.user_id is None
