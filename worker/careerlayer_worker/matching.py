import uuid
from decimal import Decimal

from sqlalchemy import delete, select

from careerlayer.integrity.models import BBox
from careerlayer.scoring import (
    ClaimInput as ScoringClaimInput,
)
from careerlayer.scoring import (
    RequirementInput as ScoringRequirementInput,
)
from careerlayer.scoring import (
    compute_match_score,
)
from careerlayer_api.llm import (
    PROMPT_VERSION_RESUME_MATCHING_V1,
    SYSTEM_PROMPT_RESUME_MATCHING_V1,
    AnthropicLLMClient,
    LLMCallResult,
    LLMClient,
    LLMError,
    MatchType,
    PrivacyGateError,
    RequirementClaim,
    ResumeMatchingOutput,
    ensure_prompt_version,
)
from careerlayer_api.models import (
    AuditLog,
    Claim,
    ClaimEvidence,
    ClaimFinding,
    Extraction,
    Finding,
    JobDescription,
    JobState,
    LLMCall,
    MatchRun,
    MatchRunState,
    ProcessingState,
    Requirement,
    Resume,
    ResumeSkill,
    TextSpan,
)
from careerlayer_api.observability import log
from careerlayer_api.settings import get_settings

from .db import session_scope


def process_match(
    match_run_id: str | uuid.UUID,
    client: LLMClient | None = None,
) -> str:
    """Evaluate a resume against a job description requirements and persist structured claims."""
    parsed_match_run_id = uuid.UUID(str(match_run_id))
    settings = get_settings()

    with session_scope() as session:
        match_run = session.get(MatchRun, parsed_match_run_id)
        if match_run is None:
            log("matching_skipped_missing_run", match_run_id=str(parsed_match_run_id))
            return "missing"

        if match_run.state == MatchRunState.COMPLETED:
            log("matching_already_completed", match_run_id=str(parsed_match_run_id))
            return "completed"

        match_run.state = MatchRunState.PROCESSING
        match_run.failure_code = None
        session.flush()

        user_id = match_run.user_id
        resume_id = match_run.resume_id
        job_id = match_run.job_description_id

        resume = session.get(Resume, resume_id)
        if resume is None or resume.state != ProcessingState.COMPLETED:
            log(
                "matching_resume_not_ready",
                match_run_id=str(parsed_match_run_id),
                resume_id=str(resume_id),
            )
            match_run.state = MatchRunState.FAILED
            match_run.failure_code = "resume_not_ready"
            session.flush()
            return "failed"

        job = session.get(JobDescription, job_id)
        if job is None or job.state != JobState.COMPLETED:
            log(
                "matching_job_not_ready",
                match_run_id=str(parsed_match_run_id),
                job_id=str(job_id),
            )
            match_run.state = MatchRunState.FAILED
            match_run.failure_code = "job_not_ready"
            session.flush()
            return "failed"

        # Load requirements
        req_query = (
            select(Requirement)
            .where(Requirement.job_description_id == job_id)
            .order_by(Requirement.ordinal.asc())
        )
        requirements = list(session.execute(req_query).scalars().all())
        if not requirements:
            log(
                "matching_no_requirements",
                match_run_id=str(parsed_match_run_id),
                job_id=str(job_id),
            )
            match_run.state = MatchRunState.FAILED
            match_run.failure_code = "no_requirements"
            session.flush()
            return "failed"

        # Load resume text spans
        span_query = (
            select(TextSpan)
            .join(Extraction, TextSpan.extraction_id == Extraction.id)
            .where(Extraction.resume_id == resume_id)
            .order_by(TextSpan.page.asc(), TextSpan.seqno.asc())
        )
        text_spans = list(session.execute(span_query).scalars().all())
        if not text_spans:
            log(
                "matching_no_spans",
                match_run_id=str(parsed_match_run_id),
                resume_id=str(resume_id),
            )
            match_run.state = MatchRunState.FAILED
            match_run.failure_code = "no_evidence"
            session.flush()
            return "failed"

        # Load findings and skills
        finding_query = select(Finding).where(Finding.resume_id == resume_id)
        findings = list(session.execute(finding_query).scalars().all())

        skill_query = select(ResumeSkill).where(ResumeSkill.resume_id == resume_id)
        skills = list(session.execute(skill_query).scalars().all())
        skills_mentioned = [s.canonical_name for s in skills]

        # Privacy is_fixture check: only fixture if both documents are fixtures
        is_fixture = bool(resume.is_fixture and job.is_fixture)

        # Ensure prompt version
        prompt_version = ensure_prompt_version(
            session,
            name=PROMPT_VERSION_RESUME_MATCHING_V1,
            purpose="matching",
            template=SYSTEM_PROMPT_RESUME_MATCHING_V1,
            model=settings.llm_model,
        )
        prompt_version_id = prompt_version.id
        prompt_version_name = prompt_version.name
        prompt_template = prompt_version.template

    # Prepare spans and requirements payloads for LLM call
    spans_payload = [{"id": str(s.id), "page": s.page, "text": s.text} for s in text_spans]

    llm = client or AnthropicLLMClient()

    # Split into batches if more than 25 requirements (Section 5)
    batch_size = 20
    req_batches: list[list[Requirement]] = []
    if len(requirements) <= 25:
        req_batches = [requirements]
    else:
        for i in range(0, len(requirements), batch_size):
            req_batches.append(requirements[i : i + batch_size])

    call_results: list[LLMCallResult[ResumeMatchingOutput]] = []
    raw_claims: list[RequirementClaim] = []
    combined_narrative: str | None = None

    for batch in req_batches:
        reqs_payload = [
            {
                "id": str(r.id),
                "kind": r.kind.value if hasattr(r.kind, "value") else str(r.kind),
                "necessity": (
                    r.necessity.value if hasattr(r.necessity, "value") else str(r.necessity)
                ),
                "criticality": r.criticality,
                "text": r.text,
            }
            for r in batch
        ]

        try:
            res = llm.match_resume_to_job(
                resume_spans=spans_payload,
                requirements=reqs_payload,
                skills_mentioned=skills_mentioned,
                is_fixture=is_fixture,
                prompt_template=prompt_template,
                prompt_version_name=prompt_version_name,
            )
            call_results.append(res)
            raw_claims.extend(res.data.claims)
            if res.data.narrative and not combined_narrative:
                combined_narrative = res.data.narrative
        except PrivacyGateError as exc:
            log("matching_blocked_privacy", match_run_id=str(parsed_match_run_id), code=exc.code)
            _fail_match_run(parsed_match_run_id, exc.code)
            return "failed"
        except LLMError as exc:
            log("matching_failed_llm", match_run_id=str(parsed_match_run_id), code=exc.code)
            _fail_match_run(parsed_match_run_id, exc.code)
            return "failed"
        except Exception as exc:
            log("matching_unhandled_error", match_run_id=str(parsed_match_run_id), error=str(exc))
            _fail_match_run(parsed_match_run_id, "matching_failed")
            return "failed"

    # Deterministic evidence grounding, citation validation, and factor calculations
    with session_scope() as session:
        match_run = session.get(MatchRun, parsed_match_run_id)
        if match_run is None:
            return "missing"

        # Record LLM call records
        for call_res in call_results:
            llm_call = LLMCall(
                user_id=user_id,
                purpose="matching",
                match_run_id=match_run.id,
                job_description_id=job_id,
                model=call_res.model,
                prompt_version_id=prompt_version_id,
                input_tokens=call_res.input_tokens,
                output_tokens=call_res.output_tokens,
                cache_read_tokens=call_res.cache_read_tokens,
                cache_write_tokens=call_res.cache_write_tokens,
                cost_usd=call_res.cost_usd,
                latency_ms=call_res.latency_ms,
                outcome="success",
                stop_reason=call_res.stop_reason,
                attempt=call_res.attempt,
            )
            session.add(llm_call)

        # Clear existing claims on this match run for idempotent retry
        session.execute(delete(Claim).where(Claim.match_run_id == match_run.id))

        spans_by_id: dict[str, TextSpan] = {str(s.id): s for s in text_spans}
        claims_by_req_id: dict[str, RequirementClaim] = {c.requirement_id: c for c in raw_claims}

        claims_rejected = 0
        claims_accepted = 0
        created_claims: list[tuple[Requirement, Claim, list[uuid.UUID]]] = []

        for req in requirements:
            req_id_str = str(req.id)
            raw_claim = claims_by_req_id.get(req_id_str)

            claim_record, evidence_spans, claim_findings, was_rejected = _build_claim_record(
                match_run_id=match_run.id,
                requirement=req,
                raw_claim=raw_claim,
                spans_by_id=spans_by_id,
                findings=findings,
            )

            if was_rejected:
                claims_rejected += 1
            else:
                claims_accepted += 1

            session.add(claim_record)
            session.flush()

            for sp_id in evidence_spans:
                ce = ClaimEvidence(claim_id=claim_record.id, span_id=sp_id)
                session.add(ce)

            for f_id in claim_findings:
                cf = ClaimFinding(claim_id=claim_record.id, finding_id=f_id)
                session.add(cf)

            created_claims.append((req, claim_record, evidence_spans))

        # Deterministic match score calculation (Phase 3E)
        scoring_reqs = [
            ScoringRequirementInput(
                id=str(r.id),
                text=r.text,
                criticality=r.criticality,
                necessity=r.necessity.value if hasattr(r.necessity, "value") else str(r.necessity),
                weight=r.weight,
            )
            for r, _, _ in created_claims
        ]

        scoring_claims = [
            ScoringClaimInput(
                requirement_id=str(c.requirement_id),
                met=c.met,
                match_type=(
                    c.match_type.value if hasattr(c.match_type, "value") else str(c.match_type)
                ),
                evidence_spans=[str(sp) for sp in ev_spans],
                satisfaction=c.satisfaction,
                corroboration=c.corroboration,
                integrity_factor=c.integrity_factor,
                evidence_quality=c.evidence_quality,
                contribution=c.contribution,
                confidence=c.confidence,
                rationale=c.rationale,
                adjacency_note=c.adjacency_note,
            )
            for _, c, ev_spans in created_claims
        ]

        score_res = compute_match_score(
            scoring_reqs,
            scoring_claims,
            scoring_version="v1",
        )

        # Update MatchRun summary fields
        total_input_tokens = sum(c.input_tokens for c in call_results)
        total_output_tokens = sum(c.output_tokens for c in call_results)
        total_cost_usd = sum(c.cost_usd for c in call_results)
        total_latency_ms = sum(c.latency_ms for c in call_results)

        match_run.state = MatchRunState.COMPLETED
        match_run.model = settings.llm_model
        match_run.prompt_version_id = prompt_version_id
        match_run.scoring_version = "v1"
        match_run.score = score_res.score
        match_run.score_if_trusted = score_res.score_if_trusted
        match_run.impact_delta = score_res.impact_delta
        match_run.requirement_count = score_res.requirement_count
        match_run.unmet_required_count = score_res.unmet_required_count
        match_run.input_tokens = total_input_tokens
        match_run.output_tokens = total_output_tokens
        match_run.cost_usd = Decimal(str(total_cost_usd)).quantize(Decimal("0.0001"))
        match_run.latency_ms = total_latency_ms
        match_run.narrative = combined_narrative
        match_run.failure_code = None

        audit = AuditLog(
            user_id=user_id,
            action="match_run_completed",
            subject_type="match_run",
            subject_id=str(match_run.id),
        )
        session.add(audit)

        log(
            "matching_completed",
            match_run_id=str(match_run.id),
            accepted_claims=claims_accepted,
            rejected_claims=claims_rejected,
            requirements_count=len(requirements),
        )

    return "completed"


def _build_claim_record(
    *,
    match_run_id: uuid.UUID,
    requirement: Requirement,
    raw_claim: RequirementClaim | None,
    spans_by_id: dict[str, TextSpan],
    findings: list[Finding],
) -> tuple[Claim, list[uuid.UUID], list[uuid.UUID], bool]:
    """Deterministically construct and validate a Claim record against stored evidence."""
    weight_applied = requirement.weight
    was_rejected = False

    if raw_claim is None:
        claim = Claim(
            match_run_id=match_run_id,
            requirement_id=requirement.id,
            met=False,
            match_type=MatchType.NONE,
            satisfaction=Decimal("0.0000"),
            corroboration=Decimal("0.0000"),
            integrity_factor=Decimal("1.0000"),
            evidence_quality=Decimal("0.0000"),
            weight_applied=weight_applied,
            contribution=Decimal("0.0000"),
            confidence=Decimal("1.0000"),
            primary_evidence_span_id=None,
            rationale="No claim provided by model for requirement.",
            adjacency_note=None,
        )
        return claim, [], [], True

    # Check for invalid adjacency: adjacent requires adjacency_note
    if raw_claim.match_type == MatchType.ADJACENT and (
        not raw_claim.adjacency_note or not raw_claim.adjacency_note.strip()
    ):
        log(
            "claim_rejected_missing_adjacency_note",
            requirement_id=str(requirement.id),
        )
        was_rejected = True

    # Filter cited span IDs to strictly those belonging to this resume
    valid_span_uuids: list[uuid.UUID] = []
    seen_spans: set[str] = set()
    for sp_id_str in raw_claim.evidence_spans:
        clean_id = sp_id_str.strip()
        if not clean_id or clean_id in seen_spans:
            continue
        if clean_id in spans_by_id:
            seen_spans.add(clean_id)
            valid_span_uuids.append(spans_by_id[clean_id].id)
        else:
            log(
                "claim_invalid_citation_dropped",
                requirement_id=str(requirement.id),
                invalid_span_id=clean_id,
            )
            was_rejected = True

    # Enforce database invariant: met = false OR primary_evidence_span_id IS NOT NULL
    is_met = bool(raw_claim.met and raw_claim.match_type != MatchType.NONE and not was_rejected)
    if is_met and not valid_span_uuids:
        log(
            "claim_rejected_met_without_valid_evidence",
            requirement_id=str(requirement.id),
        )
        is_met = False
        was_rejected = True

    if is_met:
        match_type = raw_claim.match_type
        satisfaction = Decimal("1.0000") if match_type == MatchType.DIRECT else Decimal("0.6000")
        primary_span_id = valid_span_uuids[0]

        # Corroboration formula (Section 2.3):
        # min(1.0, 0.8 + 0.1 * (distinct_spans - 1)) -> 1: 0.8, 2: 0.9, 3+: 1.0
        distinct_count = len(valid_span_uuids)
        corrob_val = min(1.0, 0.8 + 0.1 * (distinct_count - 1))
        corroboration = Decimal(str(corrob_val)).quantize(Decimal("0.0001"))

        # Integrity calculation from overlapping findings (Section 2.3)
        overlapping_finding_uuids, integrity_factor = _calculate_integrity_factor(
            valid_span_uuids=valid_span_uuids,
            spans_by_id=spans_by_id,
            findings=findings,
        )

        evidence_quality = (corroboration * integrity_factor).quantize(Decimal("0.0001"))
        contribution = (weight_applied * satisfaction * evidence_quality).quantize(
            Decimal("0.0001")
        )
        confidence_dec = Decimal(str(round(raw_claim.confidence, 4))).quantize(Decimal("0.0001"))

        claim = Claim(
            match_run_id=match_run_id,
            requirement_id=requirement.id,
            met=True,
            match_type=match_type,
            satisfaction=satisfaction,
            corroboration=corroboration,
            integrity_factor=integrity_factor,
            evidence_quality=evidence_quality,
            weight_applied=weight_applied,
            contribution=contribution,
            confidence=confidence_dec,
            primary_evidence_span_id=primary_span_id,
            rationale=raw_claim.rationale,
            adjacency_note=raw_claim.adjacency_note if match_type == MatchType.ADJACENT else None,
        )
        return claim, valid_span_uuids, overlapping_finding_uuids, was_rejected
    # Unmet or rejected claim
    confidence_dec = Decimal(str(round(raw_claim.confidence, 4))).quantize(Decimal("0.0001"))
    claim = Claim(
        match_run_id=match_run_id,
        requirement_id=requirement.id,
        met=False,
        match_type=MatchType.NONE,
        satisfaction=Decimal("0.0000"),
        corroboration=Decimal("0.0000"),
        integrity_factor=Decimal("1.0000"),
        evidence_quality=Decimal("0.0000"),
        weight_applied=weight_applied,
        contribution=Decimal("0.0000"),
        confidence=confidence_dec,
        primary_evidence_span_id=None,
        rationale=raw_claim.rationale or "Requirement not satisfied by resume evidence.",
        adjacency_note=None,
    )
    return claim, [], [], was_rejected


def _calculate_integrity_factor(
    *,
    valid_span_uuids: list[uuid.UUID],
    spans_by_id: dict[str, TextSpan],
    findings: list[Finding],
) -> tuple[list[uuid.UUID], Decimal]:
    """Find findings overlapping valid evidence spans and calculate integrity factor.

    Section 2.3:
    - Overlap: >= 50% of span's area inside finding rectangle, on the same page.
    - integrity = 0.0 if any evidence span overlaps a finding of severity 'high'
                = 0.5 else if any overlaps a finding of severity 'suspicious'
                = 1.0 otherwise (including 'info')
    """
    overlapping_finding_ids: set[uuid.UUID] = set()

    highest_severity: str = "none"

    for sp_uuid in valid_span_uuids:
        span = spans_by_id[str(sp_uuid)]
        span_bbox = BBox(x0=span.x0, y0=span.y0, x1=span.x1, y1=span.y1)

        for finding in findings:
            if finding.page != span.page:
                continue
            finding_bbox = BBox(x0=finding.x0, y0=finding.y0, x1=finding.x1, y1=finding.y1)
            if span_bbox.contained_fraction(finding_bbox) >= 0.5:
                overlapping_finding_ids.add(finding.id)
                sev = (finding.severity or "").lower()
                if sev == "high":
                    highest_severity = "high"
                elif sev == "suspicious" and highest_severity != "high":
                    highest_severity = "suspicious"
                elif sev == "info" and highest_severity == "none":
                    highest_severity = "info"

    if highest_severity == "high":
        integrity_factor = Decimal("0.0000")
    elif highest_severity == "suspicious":
        integrity_factor = Decimal("0.5000")
    else:
        integrity_factor = Decimal("1.0000")

    return list(overlapping_finding_ids), integrity_factor


def _fail_match_run(match_run_id: uuid.UUID, code: str) -> None:
    with session_scope() as session:
        match_run = session.get(MatchRun, match_run_id)
        if match_run is not None:
            match_run.state = MatchRunState.FAILED
            match_run.failure_code = code
