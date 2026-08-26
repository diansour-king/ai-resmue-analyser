from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Decimal

from .models import (
    ClaimInput,
    MatchType,
    Necessity,
    RequirementInput,
    ScoredRequirementClaim,
    ScoreResult,
)

FOUR_PLACES = Decimal("0.0001")
ONE_PLACE = Decimal("0.1")

NECESSITY_FACTORS: dict[str, Decimal] = {
    Necessity.REQUIRED.value: Decimal("1.0"),
    Necessity.PREFERRED.value: Decimal("0.4"),
}

SATISFACTION_FACTORS: dict[str, Decimal] = {
    MatchType.DIRECT.value: Decimal("1.0000"),
    MatchType.ADJACENT.value: Decimal("0.6000"),
    MatchType.NONE.value: Decimal("0.0000"),
}


def calculate_requirement_weight(
    criticality: int,
    necessity: Necessity | str,
) -> Decimal:
    """Compute requirement weight w = criticality * necessity_factor."""
    nec_key = str(necessity).lower()
    factor = NECESSITY_FACTORS.get(nec_key, Decimal("1.0"))
    return (Decimal(criticality) * factor).quantize(FOUR_PLACES)


def calculate_corroboration(distinct_spans_count: int) -> Decimal:
    """Compute corroboration factor from distinct evidence spans count."""
    if distinct_spans_count <= 0:
        return Decimal("0.0000")
    val = min(1.0, 0.8 + 0.1 * (distinct_spans_count - 1))
    return Decimal(str(val)).quantize(FOUR_PLACES)


def compute_match_score(
    requirements: Sequence[RequirementInput],
    claims: Sequence[ClaimInput],
    scoring_version: str = "v1",
) -> ScoreResult:
    """Deterministically compute the reconstructible match score and impact_delta.

    Formula (docs/phase-3-architecture.md Section 2):
        score = 100 * Σ(w_r * s_r * q_r) / Σ w_r
        score_if_trusted = 100 * Σ(w_r * s_r * q_r_trusted) / Σ w_r
        impact_delta = score_if_trusted - score

    All per-claim factors are computed/validated at NUMERIC(6,4) precision.
    Final summary scores are stored at NUMERIC(5,2) and rounded to one decimal place via
    banker's rounding.
    """

    if not requirements:
        return ScoreResult(
            score=Decimal("0.0"),
            score_if_trusted=Decimal("0.0"),
            impact_delta=Decimal("0.0"),
            raw_score=Decimal("0.0"),
            raw_score_if_trusted=Decimal("0.0"),
            requirement_count=0,
            unmet_required_count=0,
            total_weight=Decimal("0.0000"),
            total_contribution=Decimal("0.0000"),
            total_contribution_if_trusted=Decimal("0.0000"),
            claims=[],
            scoring_version=scoring_version,
        )

    claims_by_req_id: dict[str, ClaimInput] = {c.requirement_id: c for c in claims}

    scored_claims: list[ScoredRequirementClaim] = []
    total_weight = Decimal("0.0000")
    total_contribution = Decimal("0.0000")
    total_contribution_if_trusted = Decimal("0.0000")
    unmet_required_count = 0

    for req in requirements:
        req_id = str(req.id)
        nec_str = (
            req.necessity.value
            if isinstance(req.necessity, Necessity)
            else str(req.necessity).lower()
        )
        is_required = nec_str == Necessity.REQUIRED.value

        # Calculate weight
        if req.weight is not None:
            weight = Decimal(str(req.weight)).quantize(FOUR_PLACES)
        else:
            weight = calculate_requirement_weight(req.criticality, nec_str)

        total_weight += weight

        claim = claims_by_req_id.get(req_id)

        if claim is None or not claim.met or str(claim.match_type).lower() == MatchType.NONE.value:
            # Unmet requirement
            match_type_str = MatchType.NONE.value
            satisfaction = Decimal("0.0000")
            corroboration = Decimal("0.0000")
            integrity_factor = Decimal("1.0000")
            evidence_quality = Decimal("0.0000")
            contribution = Decimal("0.0000")
            contribution_if_trusted = Decimal("0.0000")
            is_req_unmet = is_required
        else:
            raw_match_type = (
                claim.match_type.value
                if isinstance(claim.match_type, MatchType)
                else str(claim.match_type).lower()
            )
            match_type_str = raw_match_type
            satisfaction = SATISFACTION_FACTORS.get(raw_match_type, Decimal("0.0000"))

            # Corroboration
            if claim.corroboration is not None:
                corroboration = Decimal(str(claim.corroboration)).quantize(FOUR_PLACES)
            else:
                distinct_spans = len(set(claim.evidence_spans))
                corroboration = calculate_corroboration(distinct_spans)

            # Integrity factor
            if claim.integrity_factor is not None:
                integrity_factor = Decimal(str(claim.integrity_factor)).quantize(FOUR_PLACES)
            else:
                integrity_factor = Decimal("1.0000")

            # Evidence qualities
            evidence_quality = (corroboration * integrity_factor).quantize(FOUR_PLACES)
            evidence_quality_trusted = (corroboration * Decimal("1.0000")).quantize(FOUR_PLACES)

            # Contributions
            contribution = (weight * satisfaction * evidence_quality).quantize(FOUR_PLACES)
            contribution_if_trusted = (weight * satisfaction * evidence_quality_trusted).quantize(
                FOUR_PLACES
            )

            # An unmet required requirement is one where contribution == 0 or integrity killed it
            is_req_unmet = is_required and (contribution == Decimal("0.0000"))

        if is_req_unmet:
            unmet_required_count += 1

        total_contribution += contribution
        total_contribution_if_trusted += contribution_if_trusted

        scored_claims.append(
            ScoredRequirementClaim(
                requirement_id=req_id,
                criticality=req.criticality,
                necessity=nec_str,
                weight=weight,
                met=bool(claim.met) if claim else False,
                match_type=match_type_str,
                satisfaction=satisfaction,
                corroboration=corroboration,
                integrity_factor=integrity_factor,
                evidence_quality=evidence_quality,
                contribution=contribution,
                contribution_if_trusted=contribution_if_trusted,
                is_required_unmet=is_req_unmet,
            )
        )

    if total_weight == Decimal("0.0000"):
        raw_score = Decimal("0.0")
        raw_score_if_trusted = Decimal("0.0")
    else:
        raw_score = (Decimal("100") * total_contribution) / total_weight
        raw_score_if_trusted = (Decimal("100") * total_contribution_if_trusted) / total_weight

    score = raw_score.quantize(ONE_PLACE, rounding=ROUND_HALF_EVEN)
    score_if_trusted = raw_score_if_trusted.quantize(ONE_PLACE, rounding=ROUND_HALF_EVEN)
    impact_delta = (score_if_trusted - score).quantize(ONE_PLACE, rounding=ROUND_HALF_EVEN)

    return ScoreResult(
        score=score,
        score_if_trusted=score_if_trusted,
        impact_delta=impact_delta,
        raw_score=raw_score,
        raw_score_if_trusted=raw_score_if_trusted,
        requirement_count=len(requirements),
        unmet_required_count=unmet_required_count,
        total_weight=total_weight,
        total_contribution=total_contribution,
        total_contribution_if_trusted=total_contribution_if_trusted,
        claims=scored_claims,
        scoring_version=scoring_version,
    )
