import uuid
from decimal import Decimal

from sqlalchemy import delete

from careerlayer_api.llm import (
    PROMPT_VERSION_JD_EXTRACTION_V1,
    SYSTEM_PROMPT_JD_EXTRACTION_V1,
    AnthropicLLMClient,
    JobRequirementExtractionOutput,
    LLMCallResult,
    LLMClient,
    LLMError,
    PrivacyGateError,
    RequirementNecessity,
    ensure_prompt_version,
)
from careerlayer_api.models import (
    AuditLog,
    JobDescription,
    JobState,
    LLMCall,
    Requirement,
)
from careerlayer_api.observability import log
from careerlayer_api.settings import get_settings

from .db import session_scope


def extract_job_requirements(
    job_id: str | uuid.UUID,
    client: LLMClient | None = None,
) -> str:
    """Extract discrete requirements from a job description using LLM with validated provenance."""
    parsed_job_id = uuid.UUID(str(job_id))
    settings = get_settings()

    with session_scope() as session:
        job = session.get(JobDescription, parsed_job_id)
        if job is None:
            log("requirement_extraction_skipped_missing", job_id=str(parsed_job_id))
            return "missing"

        is_fixture = job.is_fixture
        normalized_text = job.normalized_text
        user_id = job.user_id

        # Ensure prompt version is seeded
        prompt_version = ensure_prompt_version(
            session,
            name=PROMPT_VERSION_JD_EXTRACTION_V1,
            purpose="jd_extraction",
            template=SYSTEM_PROMPT_JD_EXTRACTION_V1,
            model=settings.llm_model,
        )
        prompt_version_id = prompt_version.id
        prompt_version_name = prompt_version.name
        prompt_template = prompt_version.template

    llm = client or AnthropicLLMClient()

    try:
        call_result: LLMCallResult[JobRequirementExtractionOutput] = llm.extract_job_requirements(
            normalized_text,
            is_fixture=is_fixture,
            prompt_template=prompt_template,
            prompt_version_name=prompt_version_name,
        )
    except PrivacyGateError as exc:
        log("requirement_extraction_blocked_privacy", job_id=str(parsed_job_id), code=exc.code)
        _record_failed_job(parsed_job_id, exc.code)
        return "failed"
    except LLMError as exc:
        log("requirement_extraction_failed_llm", job_id=str(parsed_job_id), code=exc.code)
        _record_failed_job(parsed_job_id, exc.code)
        return "failed"
    except Exception as exc:
        log(
            "requirement_extraction_unhandled_error",
            job_id=str(parsed_job_id),
            error=str(exc),
        )
        _record_failed_job(parsed_job_id, "extraction_failed")
        return "failed"

    # Persist call telemetry and validate extracted requirements
    with session_scope() as session:
        job = session.get(JobDescription, parsed_job_id)
        if job is None:
            return "missing"

        # Record LLM call
        llm_call_record = LLMCall(
            user_id=user_id,
            purpose="jd_extraction",
            job_description_id=job.id,
            match_run_id=None,
            model=call_result.model,
            prompt_version_id=prompt_version_id,
            input_tokens=call_result.input_tokens,
            output_tokens=call_result.output_tokens,
            cache_read_tokens=call_result.cache_read_tokens,
            cache_write_tokens=call_result.cache_write_tokens,
            cost_usd=call_result.cost_usd,
            latency_ms=call_result.latency_ms,
            outcome="success",
            stop_reason=call_result.stop_reason,
            attempt=call_result.attempt,
        )
        session.add(llm_call_record)

        # Validate provenance: normalized_text[start:end] == quote
        valid_requirements: list[Requirement] = []
        rejected_count = 0
        text_len = len(normalized_text)

        ordinal = 1
        for item in call_result.data.requirements:
            start = item.evidence_start
            end = item.evidence_end
            quote = item.evidence_quote

            # 1. Bounds check
            if start < 0 or end > text_len or start >= end:
                log(
                    "requirement_provenance_rejected_bounds",
                    job_id=str(job.id),
                    start=start,
                    end=end,
                    text_len=text_len,
                )
                rejected_count += 1
                continue

            # 2. Exact quote match check
            actual_text = normalized_text[start:end]
            if actual_text != quote:
                log(
                    "requirement_provenance_rejected_mismatch",
                    job_id=str(job.id),
                    expected=quote,
                    actual=actual_text,
                )
                rejected_count += 1
                continue

            # 3. Deterministic weight assignment
            crit = max(1, min(3, int(item.criticality)))
            necessity_factor = (
                Decimal("1.0")
                if item.necessity == RequirementNecessity.REQUIRED
                else Decimal("0.4")
            )
            weight = (Decimal(crit) * necessity_factor).quantize(Decimal("0.0001"))

            req_obj = Requirement(
                job_description_id=job.id,
                ordinal=ordinal,
                text=item.text.strip(),
                kind=item.kind,
                necessity=item.necessity,
                criticality=crit,
                weight=weight,
                evidence_start=start,
                evidence_end=end,
                evidence_quote=quote,
                evidence_page=None,
                evidence_bbox_x0=None,
                evidence_bbox_y0=None,
                evidence_bbox_x1=None,
                evidence_bbox_y1=None,
            )
            valid_requirements.append(req_obj)
            ordinal += 1

        # Delete any existing requirements for idempotent retry
        session.execute(delete(Requirement).where(Requirement.job_description_id == job.id))

        for req in valid_requirements:
            session.add(req)

        job.extractor_version = prompt_version_name
        job.state = JobState.COMPLETED
        job.failure_code = None

        audit = AuditLog(
            user_id=user_id,
            action="job_requirements_extracted",
            subject_type="job_description",
            subject_id=str(job.id),
        )
        session.add(audit)

        log(
            "requirement_extraction_completed",
            job_id=str(job.id),
            accepted_count=len(valid_requirements),
            rejected_count=rejected_count,
        )

    return "completed"


def _record_failed_job(job_id: uuid.UUID, code: str) -> None:
    with session_scope() as session:
        job = session.get(JobDescription, job_id)
        if job is not None:
            job.state = JobState.FAILED
            job.failure_code = code
