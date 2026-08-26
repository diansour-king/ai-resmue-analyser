from decimal import Decimal

from careerlayer.scoring import (
    ClaimInput,
    GapCategory,
    MatchType,
    Necessity,
    RequirementInput,
    classify_gap_category,
    compute_gap_analysis,
    compute_match_score,
    compute_points_available,
)
from careerlayer.scoring.projection import build_hypothetical_claims


def test_classify_gap_categories() -> None:
    # 1. Missing: match_type = none
    cat_missing = classify_gap_category(
        match_type=MatchType.NONE,
        satisfaction=Decimal("0.0000"),
        integrity_factor=Decimal("1.0000"),
    )
    assert cat_missing == GapCategory.MISSING

    # 2. Partial: match_type = adjacent
    cat_partial = classify_gap_category(
        match_type=MatchType.ADJACENT,
        satisfaction=Decimal("0.6000"),
        integrity_factor=Decimal("1.0000"),
    )
    assert cat_partial == GapCategory.PARTIAL

    # 3. Unverifiable: s > 0 but integrity < 1.0 (even if direct match!)
    cat_unverifiable = classify_gap_category(
        match_type=MatchType.DIRECT,
        satisfaction=Decimal("1.0000"),
        integrity_factor=Decimal("0.5000"),
    )
    assert cat_unverifiable == GapCategory.UNVERIFIABLE

    # 4. Unverifiable when adjacent but also flagged with tamper finding
    cat_unverifiable_adj = classify_gap_category(
        match_type=MatchType.ADJACENT,
        satisfaction=Decimal("0.6000"),
        integrity_factor=Decimal("0.2000"),
    )
    assert cat_unverifiable_adj == GapCategory.UNVERIFIABLE


def test_compute_points_available() -> None:
    # Weight = 3.0, satisfaction = 0.0, quality = 0.0 -> points = 3.0 * (1 - 0) = 3.0
    pts_missing = compute_points_available(
        weight=Decimal("3.0000"),
        satisfaction=Decimal("0.0000"),
        evidence_quality=Decimal("0.0000"),
    )
    assert pts_missing == Decimal("3.0000")

    # Weight = 2.0, satisfaction = 0.6, quality = 0.8 -> points = 2.0 * (1 - 0.48) = 1.0400
    pts_partial = compute_points_available(
        weight=Decimal("2.0000"),
        satisfaction=Decimal("0.6000"),
        evidence_quality=Decimal("0.8000"),
    )
    assert pts_partial == Decimal("1.0400")


def test_projections_match_full_hypothetical_rescore() -> None:
    """Core Phase 3H theorem: Projections match a full rescore of the same hypothetical."""
    req1 = RequirementInput(
        id="req-1",
        text="5+ years Python experience",
        criticality=3,
        necessity=Necessity.REQUIRED,
        weight=Decimal("3.0000"),
    )
    req2 = RequirementInput(
        id="req-2",
        text="Kubernetes cluster administration",
        criticality=2,
        necessity=Necessity.REQUIRED,
        weight=Decimal("2.0000"),
    )
    req3 = RequirementInput(
        id="req-3",
        text="Apache Kafka event streaming",
        criticality=2,
        necessity=Necessity.PREFERRED,
        weight=Decimal("0.8000"),
    )

    requirements = [req1, req2, req3]

    # Candidate has Python (direct clean), Kafka (adjacent clean), but lacks Kubernetes
    claims = [
        ClaimInput(
            requirement_id="req-1",
            met=True,
            match_type=MatchType.DIRECT,
            satisfaction=Decimal("1.0000"),
            corroboration=Decimal("0.8000"),
            integrity_factor=Decimal("1.0000"),
            evidence_quality=Decimal("0.8000"),
        ),
        ClaimInput(
            requirement_id="req-2",
            met=False,
            match_type=MatchType.NONE,
            satisfaction=Decimal("0.0000"),
            corroboration=Decimal("0.0000"),
            integrity_factor=Decimal("1.0000"),
            evidence_quality=Decimal("0.0000"),
        ),
        ClaimInput(
            requirement_id="req-3",
            met=True,
            match_type=MatchType.ADJACENT,
            satisfaction=Decimal("0.6000"),
            corroboration=Decimal("0.8000"),
            integrity_factor=Decimal("1.0000"),
            evidence_quality=Decimal("0.8000"),
        ),
    ]

    base_score = compute_match_score(requirements, claims)
    analysis = compute_gap_analysis(
        match_run_id="run-test",
        requirements=requirements,
        claims=claims,
        base_score_result=base_score,
    )

    assert analysis.base_score == base_score.score
    assert len(analysis.gaps) == 2  # req-2 (missing) and req-3 (partial)

    # Gap ordering: Kubernetes (w=2.0, pts=2.0) > Kafka (w=0.8, s=0.6, pts=0.8*(1-0.48)=0.416)
    assert analysis.gaps[0].requirement_id == "req-2"
    assert analysis.gaps[0].category == GapCategory.MISSING
    assert analysis.gaps[1].requirement_id == "req-3"
    assert analysis.gaps[1].category == GapCategory.PARTIAL

    # Verify single projection matches full hypothetical rescore for Kubernetes
    hypo_k8s = build_hypothetical_claims(
        requirements=requirements,
        original_claims=claims,
        clean_requirement_ids={"req-2"},
    )
    full_rescore_k8s = compute_match_score(requirements, hypo_k8s)
    assert analysis.gaps[0].projected_score == full_rescore_k8s.score

    # Verify combination projection matches full hypothetical rescore for (Kubernetes + Kafka)
    hypo_both = build_hypothetical_claims(
        requirements=requirements,
        original_claims=claims,
        clean_requirement_ids={"req-2", "req-3"},
    )
    full_rescore_both = compute_match_score(requirements, hypo_both)

    # Find the combination in analysis.combinations
    combo = next(c for c in analysis.combinations if len(c.skills) == 2)
    assert combo.projected_score == full_rescore_both.score


def test_unverifiable_gap_classification_and_projection() -> None:
    """Verify that a claim with positive satisfaction but integrity < 1.0 is unverifiable."""
    req1 = RequirementInput(
        id="req-1",
        text="AWS Solutions Architect",
        criticality=3,
        necessity=Necessity.REQUIRED,
        weight=Decimal("3.0000"),
    )

    # Direct match satisfaction, but integrity factor is discounted to 0.0
    # due to hidden white-on-white text
    claims = [
        ClaimInput(
            requirement_id="req-1",
            met=True,
            match_type=MatchType.DIRECT,
            satisfaction=Decimal("1.0000"),
            corroboration=Decimal("0.8000"),
            integrity_factor=Decimal("0.0000"),
            evidence_quality=Decimal("0.0000"),
        )
    ]

    analysis = compute_gap_analysis(
        match_run_id="run-tamper",
        requirements=[req1],
        claims=claims,
    )

    assert len(analysis.gaps) == 1
    assert analysis.gaps[0].category == GapCategory.UNVERIFIABLE
    assert analysis.gaps[0].points_available == Decimal("3.0000")
    # Clean projection gives score = 80.0
    assert analysis.gaps[0].projected_score == Decimal("80.0")
