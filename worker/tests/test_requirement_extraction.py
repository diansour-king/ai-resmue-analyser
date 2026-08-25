import uuid
from decimal import Decimal

import pytest

from careerlayer_api.llm import (
    ExtractedRequirement,
    JobRequirementExtractionOutput,
    MockLLMClient,
    RequirementKind,
    RequirementNecessity,
)
from careerlayer_api.models import JobDescription, JobSource, JobState, LLMCall, Requirement, User
from careerlayer_api.settings import get_settings
from careerlayer_worker.db import session_scope
from careerlayer_worker.requirement_extraction import extract_job_requirements


def test_requirement_extraction_provenance_and_weights(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    raw_text = "Requirements:\n- 5+ years Kubernetes\n- Go programming."
    # normalized_text will be exact same string
    normalized_text = raw_text

    with session_scope() as session:
        user = User(id=user_id, email=f"extract-user-{user_id.hex[:8]}@example.com")
        session.add(user)
        session.flush()

        job = JobDescription(
            id=job_id,
            user_id=user.id,
            title="Senior Platform Engineer",
            source=JobSource.PASTED,
            raw_text=raw_text,
            normalized_text=normalized_text,
            sha256="test-sha-extract",
            state=JobState.PROCESSING,
            is_fixture=True,
        )
        session.add(job)

    # 1. Prepare Mock output with 1 valid required, 1 invalid quote, 1 valid preferred
    req1 = ExtractedRequirement(
        text="5+ years Kubernetes experience",
        kind=RequirementKind.EXPERIENCE,
        necessity=RequirementNecessity.REQUIRED,
        criticality=3,
        evidence_start=16,
        evidence_end=35,
        evidence_quote="5+ years Kubernetes",
    )
    # Check that normalized_text[16:35] matches
    assert normalized_text[16:35] == "5+ years Kubernetes"

    req2_bad = ExtractedRequirement(
        text="Hallucinated AWS cert",
        kind=RequirementKind.CREDENTIAL,
        necessity=RequirementNecessity.REQUIRED,
        criticality=2,
        evidence_start=0,
        evidence_end=12,
        evidence_quote="AWS Solutions Architect",  # Mismatched quote -> MUST BE DROPPED
    )
    assert normalized_text[0:12] != "AWS Solutions Architect"

    req3 = ExtractedRequirement(
        text="Go programming",
        kind=RequirementKind.HARD_SKILL,
        necessity=RequirementNecessity.PREFERRED,
        criticality=2,
        evidence_start=38,
        evidence_end=52,
        evidence_quote="Go programming",
    )
    assert normalized_text[38:52] == "Go programming"

    mock_client = MockLLMClient(
        output=JobRequirementExtractionOutput(requirements=[req1, req2_bad, req3]),
        input_tokens=1200,
        output_tokens=300,
        cache_read_tokens=400,
    )

    result = extract_job_requirements(job_id, client=mock_client)
    assert result == "completed"

    with session_scope() as session:
        refreshed_job = session.get(JobDescription, job_id)
        assert refreshed_job is not None
        assert refreshed_job.state == JobState.COMPLETED
        assert refreshed_job.failure_code is None
        assert refreshed_job.extractor_version is not None

        # Verify requirements
        reqs = (
            session.query(Requirement)
            .filter_by(job_description_id=job_id)
            .order_by(Requirement.ordinal.asc())
            .all()
        )
        # Exactly 2 requirements accepted, the bad one dropped
        assert len(reqs) == 2

        # Req 1: required, crit 3 -> weight = 3.0 * 1.0 = 3.0000
        assert reqs[0].ordinal == 1
        assert reqs[0].text == "5+ years Kubernetes experience"
        assert reqs[0].necessity == RequirementNecessity.REQUIRED
        assert reqs[0].criticality == 3
        assert reqs[0].weight == Decimal("3.0000")
        assert reqs[0].evidence_quote == "5+ years Kubernetes"

        # Req 2: preferred, crit 2 -> weight = 2.0 * 0.4 = 0.8000
        assert reqs[1].ordinal == 2
        assert reqs[1].text == "Go programming"
        assert reqs[1].necessity == RequirementNecessity.PREFERRED
        assert reqs[1].criticality == 2
        assert reqs[1].weight == Decimal("0.8000")

        # Verify LLMCall telemetry recorded
        llm_calls = session.query(LLMCall).filter_by(job_description_id=job_id).all()
        assert len(llm_calls) >= 1
        call = llm_calls[0]
        assert call.purpose == "jd_extraction"
        assert call.input_tokens == 1200
        assert call.output_tokens == 300
        assert call.outcome == "success"
        assert call.cost_usd > Decimal("0")


def test_requirement_extraction_idempotency(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")

    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    text = "Requirements:\n- Python 3.11"

    with session_scope() as session:
        user = User(id=user_id, email=f"idem-extract-{user_id.hex[:8]}@example.com")
        session.add(user)
        session.flush()

        job = JobDescription(
            id=job_id,
            user_id=user.id,
            title="Python Dev",
            source=JobSource.PASTED,
            raw_text=text,
            normalized_text=text,
            sha256="sha-idem-extract",
            state=JobState.PROCESSING,
            is_fixture=True,
        )
        session.add(job)

    req = ExtractedRequirement(
        text="Python 3.11",
        kind=RequirementKind.HARD_SKILL,
        necessity=RequirementNecessity.REQUIRED,
        criticality=3,
        evidence_start=16,
        evidence_end=27,
        evidence_quote="Python 3.11",
    )
    mock_client = MockLLMClient(output=JobRequirementExtractionOutput(requirements=[req]))

    # First run
    res1 = extract_job_requirements(job_id, client=mock_client)
    assert res1 == "completed"

    # Second run (simulating worker retry or reprocessing)
    res2 = extract_job_requirements(job_id, client=mock_client)
    assert res2 == "completed"

    with session_scope() as session:
        reqs = session.query(Requirement).filter_by(job_description_id=job_id).all()
        assert len(reqs) == 1
        assert reqs[0].ordinal == 1


def test_requirement_extraction_privacy_gate_blocking(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()

    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    text = "Software Engineer job description"

    with session_scope() as session:
        user = User(id=user_id, email=f"privacy-test-{user_id.hex[:8]}@example.com")
        session.add(user)
        session.flush()

        # Real user document (is_fixture=False)
        job = JobDescription(
            id=job_id,
            user_id=user.id,
            title="Real Job",
            source=JobSource.PASTED,
            raw_text=text,
            normalized_text=text,
            sha256="sha-real-job",
            state=JobState.PROCESSING,
            is_fixture=False,
        )
        session.add(job)

    mock_client = MockLLMClient()

    # 1. fixtures_only mode blocks non-fixture document
    monkeypatch.setattr(settings, "llm_data_processing_mode", "fixtures_only")
    res1 = extract_job_requirements(job_id, client=mock_client)
    assert res1 == "failed"

    with session_scope() as session:
        refreshed = session.get(JobDescription, job_id)
        assert refreshed is not None
        assert refreshed.state == JobState.FAILED
        assert refreshed.failure_code == "privacy_gate"

    # 2. disabled mode blocks even fixture document
    monkeypatch.setattr(settings, "llm_data_processing_mode", "disabled")
    with session_scope() as session:
        job_fixture = session.get(JobDescription, job_id)
        assert job_fixture is not None
        job_fixture.is_fixture = True
        job_fixture.state = JobState.PROCESSING

    res2 = extract_job_requirements(job_id, client=mock_client)
    assert res2 == "failed"

    with session_scope() as session:
        refreshed = session.get(JobDescription, job_id)
        assert refreshed is not None
        assert refreshed.state == JobState.FAILED
        assert refreshed.failure_code == "llm_disabled"
