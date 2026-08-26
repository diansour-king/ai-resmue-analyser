from pydantic import BaseModel, Field


class BBox(BaseModel):
    """A rectangle in PDF points, origin top-left, 72 points to the inch.

    This is the only coordinate space that crosses the API boundary. The viewer converts to
    pixels itself using the page geometry in PageInfo; nothing here is in screen space and
    no scale factor is baked in, because the render DPI is a server-side decision that may
    change without the frontend being redeployed.
    """

    x0: float
    y0: float
    x1: float
    y1: float


class PageInfo(BaseModel):
    page_number: int
    width_pt: float
    height_pt: float
    rotation: int
    render_width_px: int | None
    render_height_px: int | None
    render_dpi: int | None
    render_available: bool = False
    """Whether this page has a stored render, so the viewer knows before it requests one."""


class FindingOut(BaseModel):
    finding_id: str
    detector_id: str
    detector_name: str
    severity: str
    confidence: float
    page: int
    bbox: BBox
    excerpt: str
    rationale: str


class SkillEvidenceOut(BaseModel):
    span_id: str
    page: int
    bbox: BBox
    text: str


class SkillOut(BaseModel):
    skill_id: str
    canonical_name: str
    confidence: float
    support_count: int
    flagged_support_count: int
    source: str
    evidence: list[SkillEvidenceOut]


class SeverityCounts(BaseModel):
    high: int = 0
    suspicious: int = 0
    info: int = 0


class ResumeOut(BaseModel):
    resume_id: str
    filename: str
    state: str
    page_count: int | None
    byte_size: int
    failure_code: str | None
    created_at: str
    pages: list[PageInfo] = Field(default_factory=list)
    findings_by_severity: SeverityCounts = Field(default_factory=SeverityCounts)
    skill_count: int = 0
    evidence_available: bool = False


class ResumeSummary(BaseModel):
    resume_id: str
    filename: str
    state: str
    page_count: int | None
    created_at: str


class UploadAccepted(BaseModel):
    resume_id: str
    state: str
    filename: str
    page_count: int
    duplicate_of_existing: bool


class JobCreate(BaseModel):
    title: str | None = None
    company: str | None = None
    location: str | None = None
    raw_text: str
    is_fixture: bool = False


class JobAccepted(BaseModel):
    job_description_id: str
    state: str
    source: str
    title: str | None = None
    company: str | None = None
    sha256: str
    duplicate_of_existing: bool = False


class JobSummary(BaseModel):
    job_description_id: str
    title: str | None
    company: str | None
    location: str | None
    source: str
    state: str
    created_at: str


class JobDescriptionOut(BaseModel):
    job_description_id: str
    title: str | None
    company: str | None
    location: str | None
    source: str
    state: str
    raw_text: str
    normalized_text: str
    sha256: str
    page_count: int | None
    failure_code: str | None
    extractor_version: str | None
    is_fixture: bool
    created_at: str
    updated_at: str
    requirement_count: int = 0
    findings_by_severity: SeverityCounts = Field(default_factory=SeverityCounts)


class RequirementEvidenceOut(BaseModel):
    start: int
    end: int
    quote: str
    page: int | None = None
    bbox: list[float] | None = None


class RequirementOut(BaseModel):
    requirement_id: str
    ordinal: int
    text: str
    kind: str
    necessity: str
    criticality: int
    weight: float
    evidence: RequirementEvidenceOut


class MatchCreate(BaseModel):
    resume_id: str
    job_description_id: str


class MatchAccepted(BaseModel):
    match_run_id: str
    state: str
    resume_id: str
    job_description_id: str
    reused: bool = False
    duplicate_of_existing: bool = False


class MatchJobSummary(BaseModel):
    job_description_id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None


class MatchSummary(BaseModel):
    match_run_id: str
    resume_id: str
    job_description_id: str
    state: str
    score: float | None = None
    score_if_trusted: float | None = None
    impact_delta: float | None = None
    requirement_count: int | None = None
    unmet_required_count: int | None = None
    job: MatchJobSummary
    created_at: str


class MatchListOut(BaseModel):
    items: list[MatchSummary]
    next_cursor: str | None = None


class ClaimEvidenceOut(BaseModel):
    span_id: str
    page: int
    quote: str
    bbox: list[float] | None = None


class ClaimFindingOut(BaseModel):
    finding_id: str
    detector_id: str
    detector_name: str | None = None
    severity: str


class ClaimOut(BaseModel):
    claim_id: str
    requirement_id: str
    requirement_text: str
    kind: str
    necessity: str
    criticality: int
    weight: float
    met: bool
    match_type: str
    satisfaction: float
    corroboration: float
    integrity_factor: float
    evidence_quality: float
    contribution: float
    confidence: float
    evidence: ClaimEvidenceOut | None = None
    all_evidence_spans: list[str] = Field(default_factory=list)
    findings: list[ClaimFindingOut] = Field(default_factory=list)
    rationale: str | None = None
    adjacency_note: str | None = None


class MatchRunOut(BaseModel):
    match_run_id: str
    resume_id: str
    job_description_id: str
    state: str
    model: str
    scoring_version: str
    prompt_version: str | None = None
    score: float | None = None
    score_if_trusted: float | None = None
    impact_delta: float | None = None
    requirement_count: int | None = None
    unmet_required_count: int | None = None
    job: MatchJobSummary
    claims: list[ClaimOut] = Field(default_factory=list)
    narrative: str | None = None
    failure_code: str | None = None
    token_cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: str


class GapItemOut(BaseModel):
    requirement_id: str
    skill: str
    category: str
    requirement_text: str
    necessity: str
    criticality: int
    weight: float
    current_satisfaction: float
    current_evidence_quality: float
    current_contribution: float
    points_available: float
    projected_score: float


class CandidateSkillGapOut(BaseModel):
    skill: str
    category: str
    requirement_ids: list[str]
    points_available: float
    projected_score: float


class SkillCombinationProjectionOut(BaseModel):
    skills: list[str]
    projected_score: float


class GapAnalysisOut(BaseModel):
    match_run_id: str
    base_score: float
    base_score_if_trusted: float
    impact_delta: float
    unmet_required_count: int
    gaps: list[GapItemOut] = Field(default_factory=list)
    candidates: list[CandidateSkillGapOut] = Field(default_factory=list)
    combinations: list[SkillCombinationProjectionOut] = Field(default_factory=list)
    request_id: str | None = None
