import itertools
import re
from collections.abc import Sequence
from decimal import Decimal

from .engine import FOUR_PLACES, compute_match_score
from .models import (
    CandidateSkillGap,
    ClaimInput,
    GapAnalysisResult,
    GapCategory,
    GapItem,
    MatchType,
    RequirementInput,
    ScoreResult,
    SkillCombinationProjection,
)

CLEAN_SATISFACTION = Decimal("1.0000")
CLEAN_CORROBORATION = Decimal("0.8000")
CLEAN_INTEGRITY = Decimal("1.0000")
CLEAN_EVIDENCE_QUALITY = Decimal("0.8000")


def classify_gap_category(
    match_type: MatchType | str,
    satisfaction: Decimal,
    integrity_factor: Decimal,
) -> GapCategory:
    """Classify requirement gap into one of the three architectural categories:

    - Unverifiable: s > 0 but integrity < 1.0 (resume claims it, but claim rests on flagged text)
    - Partial: match_type = adjacent (something related is shown)
    - Missing: match_type = none (the resume does not show it)
    """
    match_str = match_type.value if isinstance(match_type, MatchType) else str(match_type).lower()

    if satisfaction > Decimal("0.0000") and integrity_factor < Decimal("1.0000"):
        return GapCategory.UNVERIFIABLE
    if match_str == MatchType.ADJACENT.value:
        return GapCategory.PARTIAL
    return GapCategory.MISSING


def compute_points_available(
    weight: Decimal,
    satisfaction: Decimal,
    evidence_quality: Decimal,
) -> Decimal:
    """Compute available point uplift potential for a requirement gap:

    w * (1 - s * q)
    """
    available = weight * (Decimal("1.0000") - (satisfaction * evidence_quality))
    return max(Decimal("0.0000"), available).quantize(FOUR_PLACES)


def infer_skill_name(requirement_text: str | None) -> str:
    """Extract a concise human-readable skill label from requirement text."""
    if not requirement_text:
        return "Requirement"

    text = requirement_text.strip()
    # Strip common leading patterns like '5+ years experience in', 'Knowledge of', etc.
    cleaned = re.sub(
        r"^(?:\d+\+?\s+years(?:\s+of)?(?:\s+experience(?:\s+in|\s+with)?)?|"
        r"proficiency(?:\s+in|\s+with)?|experience(?:\s+with|\s+in)?|"
        r"strong\s+understanding\s+of|knowledge\s+of|ability\s+to|"
        r"demonstrated\s+experience\s+with)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    if not cleaned:
        cleaned = text

    # Truncate at first delimiter or after reasonable length
    for sep in [",", ";", "(", " - ", " -- "]:
        if sep in cleaned:
            cleaned = cleaned.split(sep)[0].strip()

    words = cleaned.split()
    if len(words) > 4:
        cleaned = " ".join(words[:4])

    return cleaned.title() if len(cleaned) <= 30 else cleaned[:30].strip()


def build_hypothetical_claims(
    requirements: Sequence[RequirementInput],
    original_claims: Sequence[ClaimInput],
    clean_requirement_ids: set[str],
) -> list[ClaimInput]:
    """Construct counterfactual claims where specified requirements have clean evidence."""
    claims_by_req_id: dict[str, ClaimInput] = {c.requirement_id: c for c in original_claims}
    hypothetical: list[ClaimInput] = []

    for req in requirements:
        req_id = str(req.id)
        if req_id in clean_requirement_ids:
            hypothetical.append(
                ClaimInput(
                    requirement_id=req_id,
                    met=True,
                    match_type=MatchType.DIRECT,
                    satisfaction=CLEAN_SATISFACTION,
                    corroboration=CLEAN_CORROBORATION,
                    integrity_factor=CLEAN_INTEGRITY,
                    evidence_quality=CLEAN_EVIDENCE_QUALITY,
                    evidence_spans=["hypothetical-clean-span"],
                    rationale="Counterfactual clean evidence projection.",
                )
            )
        elif req_id in claims_by_req_id:
            hypothetical.append(claims_by_req_id[req_id])
        else:
            hypothetical.append(
                ClaimInput(
                    requirement_id=req_id,
                    met=False,
                    match_type=MatchType.NONE,
                    satisfaction=Decimal("0.0000"),
                    corroboration=Decimal("0.0000"),
                    integrity_factor=Decimal("1.0000"),
                    evidence_quality=Decimal("0.0000"),
                )
            )

    return hypothetical


def compute_gap_analysis(
    match_run_id: str,
    requirements: Sequence[RequirementInput],
    claims: Sequence[ClaimInput],
    base_score_result: ScoreResult | None = None,
    max_candidates: int = 5,
    scoring_version: str = "v1",
) -> GapAnalysisResult:
    """Deterministically compute requirement gaps and server-projected counterfactual scores.

    1. Identifies all gaps (contribution == 0, satisfaction < 1.0, or integrity < 1.0).
    2. Classifies gaps into Missing, Partial, or Unverifiable.
    3. Calculates points available: w * (1 - s * q).
    4. Computes exact single-gap and combination projections by re-running deterministic scoring.
    """
    if base_score_result is None:
        base_score_result = compute_match_score(
            requirements, claims, scoring_version=scoring_version
        )

    scored_claims_by_req_id = {c.requirement_id: c for c in base_score_result.claims}

    gap_items: list[GapItem] = []

    for req in requirements:
        req_id = str(req.id)
        scored = scored_claims_by_req_id.get(req_id)

        if scored is None:
            continue

        # A gap exists if satisfaction < 1.0, contribution == 0, or integrity < 1.0
        is_gap = (
            scored.contribution == Decimal("0.0000")
            or scored.satisfaction < Decimal("1.0000")
            or scored.integrity_factor < Decimal("1.0000")
        )

        if not is_gap:
            continue

        category = classify_gap_category(
            match_type=scored.match_type,
            satisfaction=scored.satisfaction,
            integrity_factor=scored.integrity_factor,
        )

        points_available = compute_points_available(
            weight=scored.weight,
            satisfaction=scored.satisfaction,
            evidence_quality=scored.evidence_quality,
        )

        # Single requirement projection via full hypothetical rescore
        single_hypo = build_hypothetical_claims(
            requirements=requirements,
            original_claims=claims,
            clean_requirement_ids={req_id},
        )
        single_res = compute_match_score(
            requirements=requirements,
            claims=single_hypo,
            scoring_version=scoring_version,
        )

        skill_label = infer_skill_name(req.text)

        gap_items.append(
            GapItem(
                requirement_id=req_id,
                skill=skill_label,
                category=category,
                requirement_text=req.text or f"Requirement {req_id}",
                necessity=scored.necessity,
                criticality=scored.criticality,
                weight=scored.weight,
                current_satisfaction=scored.satisfaction,
                current_evidence_quality=scored.evidence_quality,
                current_contribution=scored.contribution,
                points_available=points_available,
                projected_score=single_res.score,
            )
        )

    # Sort gaps by points_available descending
    gap_items.sort(key=lambda g: g.points_available, reverse=True)

    # Select top candidate skill gaps
    candidates: list[CandidateSkillGap] = []
    seen_skills: set[str] = set()

    for item in gap_items:
        if len(candidates) >= max_candidates:
            break
        # Group requirements that share the same skill label
        if item.skill in seen_skills:
            continue
        seen_skills.add(item.skill)

        linked_req_ids = [g.requirement_id for g in gap_items if g.skill == item.skill]
        # Rescore for all requirements linked to this skill
        skill_hypo = build_hypothetical_claims(
            requirements=requirements,
            original_claims=claims,
            clean_requirement_ids=set(linked_req_ids),
        )
        skill_res = compute_match_score(
            requirements=requirements,
            claims=skill_hypo,
            scoring_version=scoring_version,
        )

        # Total points available across linked requirements
        total_pts = sum(
            (g.points_available for g in gap_items if g.skill == item.skill),
            start=Decimal("0.0000"),
        ).quantize(FOUR_PLACES)

        candidates.append(
            CandidateSkillGap(
                skill=item.skill,
                category=item.category,
                requirement_ids=linked_req_ids,
                points_available=total_pts,
                projected_score=skill_res.score,
            )
        )

    # Precompute subset combinations (size 2 up to len(candidates))
    combinations: list[SkillCombinationProjection] = []
    for k in range(2, len(candidates) + 1):
        for combo in itertools.combinations(candidates, k):
            combo_skills = sorted([c.skill for c in combo])
            combo_req_ids = set()
            for c in combo:
                combo_req_ids.update(c.requirement_ids)

            combo_hypo = build_hypothetical_claims(
                requirements=requirements,
                original_claims=claims,
                clean_requirement_ids=combo_req_ids,
            )
            combo_res = compute_match_score(
                requirements=requirements,
                claims=combo_hypo,
                scoring_version=scoring_version,
            )

            combinations.append(
                SkillCombinationProjection(
                    skills=combo_skills,
                    projected_score=combo_res.score,
                )
            )

    return GapAnalysisResult(
        match_run_id=match_run_id,
        base_score=base_score_result.score,
        base_score_if_trusted=base_score_result.score_if_trusted,
        impact_delta=base_score_result.impact_delta,
        unmet_required_count=base_score_result.unmet_required_count,
        gaps=gap_items,
        candidates=candidates,
        combinations=combinations,
    )
