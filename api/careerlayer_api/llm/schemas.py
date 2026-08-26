from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..models.job import RequirementKind, RequirementNecessity
from ..models.match import MatchType

__all__ = [
    "ExtractedRequirement",
    "JobRequirementExtractionOutput",
    "RequirementClaim",
    "RequirementKind",
    "RequirementNecessity",
    "ResumeMatchingOutput",
    "get_jd_extraction_json_schema",
    "get_resume_matching_json_schema",
]


class ExtractedRequirement(BaseModel):
    text: str = Field(
        ...,
        description="The requirement restated as a single testable statement.",
    )
    kind: RequirementKind = Field(
        ...,
        description="The requirement category: hard_skill, soft_skill, experience, or credential.",
    )
    necessity: RequirementNecessity = Field(
        ...,
        description="Whether the requirement is required or preferred.",
    )
    criticality: int = Field(
        ...,
        ge=1,
        le=3,
        description="Criticality score from 1 to 3 based on the published rubric.",
    )
    evidence_start: int = Field(
        ...,
        ge=0,
        description="Character start offset within the normalized job description text.",
    )
    evidence_end: int = Field(
        ...,
        ge=0,
        description="Character end offset within the normalized job description text.",
    )
    evidence_quote: str = Field(
        ...,
        description="Exact substring from the job description between start and end offsets.",
    )

    @field_validator("kind", mode="before")
    @classmethod
    def _coerce_kind(cls, value: Any) -> Any:
        if isinstance(value, str):
            v_norm = value.strip().lower()
            for k in RequirementKind:
                if k.value == v_norm:
                    return k
        return value

    @field_validator("necessity", mode="before")
    @classmethod
    def _coerce_necessity(cls, value: Any) -> Any:
        if isinstance(value, str):
            v_norm = value.strip().lower()
            for n in RequirementNecessity:
                if n.value == v_norm:
                    return n
        return value


class JobRequirementExtractionOutput(BaseModel):
    requirements: list[ExtractedRequirement] = Field(
        default_factory=list,
        description="List of extracted job requirements with provenance.",
    )


def get_jd_extraction_json_schema() -> dict[str, Any]:
    """Return the JSON schema dictionary for structured output decoding."""
    return JobRequirementExtractionOutput.model_json_schema()


class RequirementClaim(BaseModel):
    requirement_id: str = Field(
        ...,
        description="The UUID string of the requirement being evaluated.",
    )
    met: bool = Field(
        ...,
        description="Whether the candidate meets this requirement.",
    )
    match_type: MatchType = Field(
        ...,
        description="The match type: direct, adjacent, or none.",
    )
    evidence_spans: list[str] = Field(
        default_factory=list,
        description="List of span_id strings from the resume supporting this claim.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Model self-reported confidence between 0.0 and 1.0.",
    )
    rationale: str | None = Field(
        default=None,
        description="Concise rationale explaining the evaluation.",
    )
    adjacency_note: str | None = Field(
        default=None,
        description="Explanation of transferable relationship if match_type is adjacent.",
    )

    @field_validator("match_type", mode="before")
    @classmethod
    def _coerce_match_type(cls, value: Any) -> Any:
        if isinstance(value, str):
            v_norm = value.strip().lower()
            for m in MatchType:
                if m.value == v_norm:
                    return m
        return value

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, value: Any) -> Any:
        if isinstance(value, (int, float, str)):
            try:
                f_val = float(value)
                return max(0.0, min(1.0, f_val))
            except ValueError:
                return 1.0
        return value


class ResumeMatchingOutput(BaseModel):
    claims: list[RequirementClaim] = Field(
        default_factory=list,
        description="List of requirement claims evaluated against the resume.",
    )
    narrative: str | None = Field(
        default=None,
        description="Human-readable summary narrative of the candidate's alignment.",
    )


def get_resume_matching_json_schema() -> dict[str, Any]:
    """Return the JSON schema dictionary for structured output decoding of resume matching."""
    return ResumeMatchingOutput.model_json_schema()
