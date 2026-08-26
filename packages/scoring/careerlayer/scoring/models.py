from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Necessity(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class MatchType(StrEnum):
    DIRECT = "direct"
    ADJACENT = "adjacent"
    NONE = "none"


class RequirementInput(BaseModel):
    """Input representation of an extracted requirement for scoring."""

    model_config = ConfigDict(frozen=True)

    id: str
    text: str | None = None
    criticality: int = Field(ge=1, le=3, description="Criticality: 1, 2, or 3")
    necessity: Necessity | str = Necessity.REQUIRED
    weight: Decimal | None = None


class ClaimInput(BaseModel):
    """Input representation of a requirement claim for scoring."""

    model_config = ConfigDict(frozen=True)

    requirement_id: str
    met: bool
    match_type: MatchType | str
    evidence_spans: list[str] = Field(default_factory=list)
    satisfaction: Decimal | None = None
    corroboration: Decimal | None = None
    integrity_factor: Decimal | None = None
    evidence_quality: Decimal | None = None
    contribution: Decimal | None = None
    confidence: Decimal | float | None = None
    rationale: str | None = None
    adjacency_note: str | None = None


class ScoredRequirementClaim(BaseModel):
    """Detailed breakdown of a scored requirement."""

    model_config = ConfigDict(frozen=True)

    requirement_id: str
    criticality: int
    necessity: str
    weight: Decimal
    met: bool
    match_type: str
    satisfaction: Decimal
    corroboration: Decimal
    integrity_factor: Decimal
    evidence_quality: Decimal
    contribution: Decimal
    contribution_if_trusted: Decimal
    is_required_unmet: bool


class ScoreResult(BaseModel):
    """Result of deterministic match scoring."""

    model_config = ConfigDict(frozen=True)

    score: Decimal
    score_if_trusted: Decimal
    impact_delta: Decimal
    raw_score: Decimal
    raw_score_if_trusted: Decimal
    requirement_count: int
    unmet_required_count: int
    total_weight: Decimal
    total_contribution: Decimal
    total_contribution_if_trusted: Decimal
    claims: list[ScoredRequirementClaim]
    scoring_version: str = "v1"


class GapCategory(StrEnum):
    MISSING = "missing"
    PARTIAL = "partial"
    UNVERIFIABLE = "unverifiable"


class GapItem(BaseModel):
    """A requirement gap representing unmet, partial, or untrusted evidence."""

    model_config = ConfigDict(frozen=True)

    requirement_id: str
    skill: str
    category: GapCategory
    requirement_text: str
    necessity: str
    criticality: int
    weight: Decimal
    current_satisfaction: Decimal
    current_evidence_quality: Decimal
    current_contribution: Decimal
    points_available: Decimal
    projected_score: Decimal


class CandidateSkillGap(BaseModel):
    """A high-value skill gap candidate for counterfactual simulation."""

    model_config = ConfigDict(frozen=True)

    skill: str
    category: GapCategory
    requirement_ids: list[str]
    points_available: Decimal
    projected_score: Decimal


class SkillCombinationProjection(BaseModel):
    """Precomputed projected score for a combination of candidate skills."""

    model_config = ConfigDict(frozen=True)

    skills: list[str]
    projected_score: Decimal


class GapAnalysisResult(BaseModel):
    """Complete gap analysis and precomputed counterfactual projections."""

    model_config = ConfigDict(frozen=True)

    match_run_id: str
    base_score: Decimal
    base_score_if_trusted: Decimal
    impact_delta: Decimal
    unmet_required_count: int
    gaps: list[GapItem]
    candidates: list[CandidateSkillGap]
    combinations: list[SkillCombinationProjection]
