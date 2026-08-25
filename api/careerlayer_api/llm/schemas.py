from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..models.job import RequirementKind, RequirementNecessity

__all__ = [
    "ExtractedRequirement",
    "JobRequirementExtractionOutput",
    "RequirementKind",
    "RequirementNecessity",
    "get_jd_extraction_json_schema",
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
