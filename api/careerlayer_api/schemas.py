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
