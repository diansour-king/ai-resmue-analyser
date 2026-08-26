import uuid
from decimal import Decimal

import pytest

from careerlayer_api.llm import (
    MatchType,
    MockLLMClient,
    RequirementClaim,
    ResumeMatchingOutput,
)
from careerlayer_api.models import (
    Claim,
    ClaimEvidence,
    ClaimFinding,
    Extraction,
    Finding,
    JobDescription,
    JobSource,
    JobState,
    LLMCall,
    MatchRun,
    MatchRunState,
    ProcessingState,
    Requirement,
    RequirementKind,
    RequirementNecessity,
    Resume,
    ResumeSkill,
    TextSpan,
    User,
)
from careerlayer_api.settings import get_settings
from careerlayer_worker.db import session_scope
from careerlayer_worker.matching import process_match


def _setup_match_fixture(
    *,
    is_fixture: bool = True,
    resume_state: ProcessingState = ProcessingState.COMPLETED,
    job_state: JobState = JobState.COMPLETED,
    has_spans: bool = True,
    has_reqs: bool = True,
    add_d1_finding: bool = False,
    d1_severity: str = "high",
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, list[uuid.UUID], list[uuid.UUID]]:
    """Helper to set up a complete test database fixture for matching tests."""
    user_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    job_id = uuid.uuid4()
    match_run_id = uuid.uuid4()
    span_ids: list[uuid.UUID] = []
    req_ids: list[uuid.UUID] = []

    with session_scope() as session:
        user = User(id=user_id, email=f"match-user-{user_id.hex[:8]}@example.com")
        session.add(user)
        session.flush()

        resume = Resume(
            id=resume_id,
            user_id=user.id,
            filename="test_resume.pdf",
            storage_key="test_resume_key",
            sha256=f"sha-res-{user_id.hex[:8]}",
            byte_size=12345,
            page_count=2,
            state=resume_state,
            is_fixture=is_fixture,
        )
        session.add(resume)
        session.flush()

        if has_spans:
            extraction = Extraction(
                id=uuid.uuid4(),
                resume_id=resume.id,
                method="pdfminer",
                page_count=2,
                duration_ms=100,
            )
            session.add(extraction)
            session.flush()

            # Span 1: Clean span (page 1, top)
            s1 = TextSpan(
                id=uuid.uuid4(),
                extraction_id=extraction.id,
                page=1,
                seqno=0,
                x0=50.0,
                y0=100.0,
                x1=300.0,
                y1=120.0,
                text="Senior Software Engineer with 6+ years Python and FastAPI experience",
                font="Helvetica",
                font_size=12.0,
                colour="#000000",
                render_mode=0,
                opacity=1.0,
                char_start=0,
                char_end=70,
            )
            # Span 2: Clean span (page 1, middle)
            s2 = TextSpan(
                id=uuid.uuid4(),
                extraction_id=extraction.id,
                page=1,
                seqno=1,
                x0=50.0,
                y0=150.0,
                x1=300.0,
                y1=170.0,
                text="Architected distributed event streaming platform with Redis Streams",
                font="Helvetica",
                font_size=12.0,
                colour="#000000",
                render_mode=0,
                opacity=1.0,
                char_start=71,
                char_end=140,
            )
            # Span 3: Flagged or clean span (page 1, bottom)
            s3 = TextSpan(
                id=uuid.uuid4(),
                extraction_id=extraction.id,
                page=1,
                seqno=2,
                x0=50.0,
                y0=700.0,
                x1=300.0,
                y1=720.0,
                text="Expert in Kubernetes cluster deployment and operations in production",
                font="Helvetica",
                font_size=12.0,
                colour="#000000",
                render_mode=0,
                opacity=1.0,
                char_start=141,
                char_end=210,
            )
            session.add_all([s1, s2, s3])
            session.flush()
            span_ids = [s1.id, s2.id, s3.id]

            # Optional finding on span 3
            if add_d1_finding:
                finding = Finding(
                    id=uuid.uuid4(),
                    resume_id=resume.id,
                    detector_id="D1",
                    detector_name="Invisible text render mode",
                    severity=d1_severity,
                    confidence=0.99,
                    page=1,
                    x0=45.0,
                    y0=695.0,
                    x1=305.0,
                    y1=725.0,
                    excerpt="Expert in Kubernetes cluster deployment",
                    rationale="Render mode 3 invisible text",
                )
                session.add(finding)
                session.flush()

            # Add sample resume skill
            skill = ResumeSkill(
                id=uuid.uuid4(),
                resume_id=resume.id,
                canonical_name="Python",
                source="dictionary_v1",
                confidence=0.9,
                support_count=1,
                flagged_support_count=0,
            )
            session.add(skill)

        job = JobDescription(
            id=job_id,
            user_id=user.id,
            title="Senior Backend Engineer",
            source=JobSource.PASTED,
            raw_text="Job Description text",
            normalized_text="Job Description text",
            sha256=f"sha-job-{user_id.hex[:8]}",
            state=job_state,
            is_fixture=is_fixture,
        )
        session.add(job)
        session.flush()

        if has_reqs:
            # Req 1: Python (required, crit 3 -> weight 3.0)
            r1 = Requirement(
                id=uuid.uuid4(),
                job_description_id=job.id,
                ordinal=1,
                text="5+ years Python in production",
                kind=RequirementKind.HARD_SKILL,
                necessity=RequirementNecessity.REQUIRED,
                criticality=3,
                weight=Decimal("3.0000"),
                evidence_start=0,
                evidence_end=10,
                evidence_quote="Python",
            )
            # Req 2: Kafka (preferred, crit 2 -> weight 0.8)
            r2 = Requirement(
                id=uuid.uuid4(),
                job_description_id=job.id,
                ordinal=2,
                text="Kafka or distributed event streaming",
                kind=RequirementKind.HARD_SKILL,
                necessity=RequirementNecessity.PREFERRED,
                criticality=2,
                weight=Decimal("0.8000"),
                evidence_start=11,
                evidence_end=16,
                evidence_quote="Kafka",
            )
            # Req 3: Kubernetes (required, crit 3 -> weight 3.0)
            r3 = Requirement(
                id=uuid.uuid4(),
                job_description_id=job.id,
                ordinal=3,
                text="Kubernetes cluster management",
                kind=RequirementKind.HARD_SKILL,
                necessity=RequirementNecessity.REQUIRED,
                criticality=3,
                weight=Decimal("3.0000"),
                evidence_start=17,
                evidence_end=27,
                evidence_quote="Kubernetes",
            )
            session.add_all([r1, r2, r3])
            session.flush()
            req_ids = [r1.id, r2.id, r3.id]

        match_run = MatchRun(
            id=match_run_id,
            user_id=user.id,
            resume_id=resume.id,
            job_description_id=job.id,
            state=MatchRunState.QUEUED,
            model="claude-sonnet-5",
            scoring_version="v1",
        )
        session.add(match_run)
        session.flush()

    return user_id, resume_id, job_id, match_run_id, span_ids, req_ids


def test_valid_match_run_and_claim_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    _, _, _, match_run_id, span_ids, req_ids = _setup_match_fixture()

    c1 = RequirementClaim(
        requirement_id=str(req_ids[0]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[str(span_ids[0])],
        confidence=0.98,
        rationale="Strong Python experience cited.",
        adjacency_note=None,
    )
    c2 = RequirementClaim(
        requirement_id=str(req_ids[1]),
        met=True,
        match_type=MatchType.ADJACENT,
        evidence_spans=[str(span_ids[1])],
        confidence=0.85,
        rationale="Redis Streams transferable to Kafka.",
        adjacency_note="Redis Streams provides event streaming semantics.",
    )
    c3 = RequirementClaim(
        requirement_id=str(req_ids[2]),
        met=False,
        match_type=MatchType.NONE,
        evidence_spans=[],
        confidence=0.9,
        rationale="No Kubernetes experience listed.",
        adjacency_note=None,
    )

    mock_client = MockLLMClient(
        matching_output=ResumeMatchingOutput(
            claims=[c1, c2, c3],
            narrative="Candidate is strong in Python and distributed systems.",
        ),
        input_tokens=2200,
        output_tokens=600,
        cache_read_tokens=500,
    )

    res = process_match(match_run_id, client=mock_client)
    assert res == "completed"

    with session_scope() as session:
        match_run = session.get(MatchRun, match_run_id)
        assert match_run is not None
        assert match_run.state == MatchRunState.COMPLETED
        assert match_run.failure_code is None
        assert match_run.requirement_count == 3
        assert match_run.score == Decimal("40.9")
        assert match_run.score_if_trusted == Decimal("40.9")
        assert match_run.impact_delta == Decimal("0.0")
        assert match_run.unmet_required_count == 1
        assert match_run.narrative == "Candidate is strong in Python and distributed systems."

        assert match_run.cost_usd is not None and match_run.cost_usd > Decimal("0")
        assert match_run.input_tokens == 2200
        assert match_run.output_tokens == 600

        claims = (
            session.query(Claim)
            .filter_by(match_run_id=match_run_id)
            .order_by(Claim.created_at.asc())
            .all()
        )
        assert len(claims) == 3

        # Claim 1: Direct, 1 span -> corrob 0.8, integrity 1.0 -> q = 0.8,
        # contrib = 3.0 * 1.0 * 0.8 = 2.4
        claim1 = next(c for c in claims if c.requirement_id == req_ids[0])

        assert claim1.met is True
        assert claim1.match_type == MatchType.DIRECT
        assert claim1.satisfaction == Decimal("1.0000")
        assert claim1.corroboration == Decimal("0.8000")
        assert claim1.integrity_factor == Decimal("1.0000")
        assert claim1.evidence_quality == Decimal("0.8000")
        assert claim1.weight_applied == Decimal("3.0000")
        assert claim1.contribution == Decimal("2.4000")
        assert claim1.primary_evidence_span_id == span_ids[0]

        # ClaimEvidence persisted
        ce1 = session.query(ClaimEvidence).filter_by(claim_id=claim1.id).all()
        assert len(ce1) == 1
        assert ce1[0].span_id == span_ids[0]

        # Claim 2: Adjacent, 1 span -> satisfaction 0.6, q 0.8, w 0.8 -> contrib = 0.3840
        claim2 = next(c for c in claims if c.requirement_id == req_ids[1])
        assert claim2.met is True
        assert claim2.match_type == MatchType.ADJACENT
        assert claim2.satisfaction == Decimal("0.6000")
        assert claim2.corroboration == Decimal("0.8000")
        assert claim2.evidence_quality == Decimal("0.8000")
        assert claim2.contribution == Decimal("0.3840")
        assert claim2.adjacency_note == "Redis Streams provides event streaming semantics."

        # Claim 3: None -> met False, contrib 0.0, primary_span None
        claim3 = next(c for c in claims if c.requirement_id == req_ids[2])
        assert claim3.met is False
        assert claim3.match_type == MatchType.NONE
        assert claim3.satisfaction == Decimal("0.0000")
        assert claim3.contribution == Decimal("0.0000")
        assert claim3.primary_evidence_span_id is None

        # Verify LLMCall telemetry recorded
        llm_calls = session.query(LLMCall).filter_by(match_run_id=match_run_id).all()
        assert len(llm_calls) >= 1
        assert llm_calls[0].purpose == "matching"
        assert llm_calls[0].input_tokens == 2200


def test_corroboration_scaling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert corroboration scaling: 1 span -> 0.8, 2 spans -> 0.9, 3+ spans -> 1.0."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    _, _, _, match_run_id, span_ids, req_ids = _setup_match_fixture()

    # R1: 3 spans -> corrob 1.0
    c1 = RequirementClaim(
        requirement_id=str(req_ids[0]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[str(span_ids[0]), str(span_ids[1]), str(span_ids[2])],
        confidence=1.0,
        rationale="Supported across 3 spans.",
    )
    # R2: 2 spans -> corrob 0.9
    c2 = RequirementClaim(
        requirement_id=str(req_ids[1]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[str(span_ids[0]), str(span_ids[1])],
        confidence=1.0,
        rationale="Supported across 2 spans.",
    )
    # R3: 1 span -> corrob 0.8
    c3 = RequirementClaim(
        requirement_id=str(req_ids[2]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[str(span_ids[0])],
        confidence=1.0,
        rationale="Supported across 1 span.",
    )

    mock_client = MockLLMClient(matching_output=ResumeMatchingOutput(claims=[c1, c2, c3]))
    process_match(match_run_id, client=mock_client)

    with session_scope() as session:
        claims = session.query(Claim).filter_by(match_run_id=match_run_id).all()
        cl1 = next(c for c in claims if c.requirement_id == req_ids[0])
        assert cl1.corroboration == Decimal("1.0000")
        assert cl1.evidence_quality == Decimal("1.0000")

        cl2 = next(c for c in claims if c.requirement_id == req_ids[1])
        assert cl2.corroboration == Decimal("0.9000")
        assert cl2.evidence_quality == Decimal("0.9000")

        cl3 = next(c for c in claims if c.requirement_id == req_ids[2])
        assert cl3.corroboration == Decimal("0.8000")
        assert cl3.evidence_quality == Decimal("0.8000")


def test_integrity_aware_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify high severity integrity finding zeroes integrity_factor and adds ClaimFinding."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    # Set up with D1 high severity finding on span 3
    _, _, _, match_run_id, span_ids, req_ids = _setup_match_fixture(
        add_d1_finding=True,
        d1_severity="high",
    )

    # Claim for R3 rests solely on span 3 (which has D1 high finding)
    c3 = RequirementClaim(
        requirement_id=str(req_ids[2]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[str(span_ids[2])],
        confidence=0.95,
        rationale="Kubernetes experience cited.",
    )
    mock_client = MockLLMClient(matching_output=ResumeMatchingOutput(claims=[c3]))
    process_match(match_run_id, client=mock_client)

    with session_scope() as session:
        claims = session.query(Claim).filter_by(match_run_id=match_run_id).all()
        cl3 = next(c for c in claims if c.requirement_id == req_ids[2])

        # Integrity factor MUST be 0.0000 for high severity finding
        assert cl3.integrity_factor == Decimal("0.0000")
        assert cl3.evidence_quality == Decimal("0.0000")
        assert cl3.contribution == Decimal("0.0000")

        # Verify claim_findings association
        c_findings = session.query(ClaimFinding).filter_by(claim_id=cl3.id).all()
        assert len(c_findings) == 1

        match_run = session.get(MatchRun, match_run_id)
        assert match_run is not None
        assert match_run.score == Decimal("0.0")
        assert match_run.score_if_trusted == Decimal("35.3")
        assert match_run.impact_delta == Decimal("35.3")
        assert match_run.unmet_required_count == 2


def test_integrity_suspicious_severity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify suspicious severity integrity finding halves integrity_factor (0.5)."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    _, _, _, match_run_id, span_ids, req_ids = _setup_match_fixture(
        add_d1_finding=True,
        d1_severity="suspicious",
    )

    c3 = RequirementClaim(
        requirement_id=str(req_ids[2]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[str(span_ids[2])],
        confidence=0.95,
        rationale="Kubernetes experience cited.",
    )
    mock_client = MockLLMClient(matching_output=ResumeMatchingOutput(claims=[c3]))
    process_match(match_run_id, client=mock_client)

    with session_scope() as session:
        claims = session.query(Claim).filter_by(match_run_id=match_run_id).all()
        cl3 = next(c for c in claims if c.requirement_id == req_ids[2])
        assert cl3.integrity_factor == Decimal("0.5000")
        assert cl3.corroboration == Decimal("0.8000")
        assert cl3.evidence_quality == Decimal("0.4000")
        # contribution = 3.0 * 1.0 * 0.4000 = 1.2000
        assert cl3.contribution == Decimal("1.2000")


def test_citation_validation_and_hallucination_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify invalid / hallucinated span IDs are dropped and invalid claims rejected."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    _, _, _, match_run_id, span_ids, req_ids = _setup_match_fixture()

    # 1. Claim citing fake hallucinated span ID
    fake_span_id = str(uuid.uuid4())
    c1_fake = RequirementClaim(
        requirement_id=str(req_ids[0]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[fake_span_id],
        confidence=0.95,
        rationale="Hallucinated span citation.",
    )
    # 2. Claim with adjacent match type but missing adjacency_note -> MUST BE REJECTED
    c2_bad_adj = RequirementClaim(
        requirement_id=str(req_ids[1]),
        met=True,
        match_type=MatchType.ADJACENT,
        evidence_spans=[str(span_ids[1])],
        confidence=0.9,
        rationale="Adjacent experience.",
        adjacency_note=None,  # Missing note -> rejected
    )

    mock_client = MockLLMClient(matching_output=ResumeMatchingOutput(claims=[c1_fake, c2_bad_adj]))
    process_match(match_run_id, client=mock_client)

    with session_scope() as session:
        claims = session.query(Claim).filter_by(match_run_id=match_run_id).all()

        # Claim 1: hallucinated span dropped -> 0 valid spans -> met=False, match_type=none
        cl1 = next(c for c in claims if c.requirement_id == req_ids[0])
        assert cl1.met is False
        assert cl1.match_type == MatchType.NONE
        assert cl1.primary_evidence_span_id is None
        assert cl1.contribution == Decimal("0.0000")

        # Claim 2: missing adjacency note -> rejected -> met=False, match_type=none
        cl2 = next(c for c in claims if c.requirement_id == req_ids[1])
        assert cl2.met is False
        assert cl2.match_type == MatchType.NONE
        assert cl2.contribution == Decimal("0.0000")


def test_matching_idempotency_and_safe_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    _, _, _, match_run_id, span_ids, req_ids = _setup_match_fixture()

    c1 = RequirementClaim(
        requirement_id=str(req_ids[0]),
        met=True,
        match_type=MatchType.DIRECT,
        evidence_spans=[str(span_ids[0])],
        confidence=0.95,
        rationale="Valid Python claim.",
    )
    mock_client = MockLLMClient(matching_output=ResumeMatchingOutput(claims=[c1]))

    # First run
    res1 = process_match(match_run_id, client=mock_client)
    assert res1 == "completed"

    # Second run on completed run -> skips gracefully
    res2 = process_match(match_run_id, client=mock_client)
    assert res2 == "completed"

    with session_scope() as session:
        claims = session.query(Claim).filter_by(match_run_id=match_run_id).all()
        # Exactly 3 claims (one per requirement), not 6
        assert len(claims) == 3


def test_missing_dependencies_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    # 1. Non-existent match run
    res_missing = process_match(uuid.uuid4())
    assert res_missing == "missing"

    # 2. Resume not completed
    _, _, _, run_bad_resume, _, _ = _setup_match_fixture(resume_state=ProcessingState.QUEUED)
    res_bad_res = process_match(run_bad_resume)
    assert res_bad_res == "failed"

    with session_scope() as session:
        mr = session.get(MatchRun, run_bad_resume)
        assert mr is not None
        assert mr.state == MatchRunState.FAILED
        assert mr.failure_code == "resume_not_ready"

    # 3. Job not completed
    _, _, _, run_bad_job, _, _ = _setup_match_fixture(job_state=JobState.PROCESSING)
    res_bad_job = process_match(run_bad_job)
    assert res_bad_job == "failed"

    with session_scope() as session:
        mr = session.get(MatchRun, run_bad_job)
        assert mr is not None
        assert mr.state == MatchRunState.FAILED
        assert mr.failure_code == "job_not_ready"

    # 4. Job has no requirements
    _, _, _, run_no_reqs, _, _ = _setup_match_fixture(has_reqs=False)
    res_no_reqs = process_match(run_no_reqs)
    assert res_no_reqs == "failed"

    with session_scope() as session:
        mr = session.get(MatchRun, run_no_reqs)
        assert mr is not None
        assert mr.state == MatchRunState.FAILED
        assert mr.failure_code == "no_requirements"


def test_privacy_gate_blocking_in_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()

    # Real user document (is_fixture=False) in fixtures_only mode
    _, _, _, match_run_id, _, _ = _setup_match_fixture(is_fixture=False)

    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")
    mock_client = MockLLMClient()

    res = process_match(match_run_id, client=mock_client)
    assert res == "failed"

    with session_scope() as session:
        mr = session.get(MatchRun, match_run_id)
        assert mr is not None
        assert mr.state == MatchRunState.FAILED
        assert mr.failure_code == "privacy_gate"
