export type BBox = { x0: number; y0: number; x1: number; y1: number };

export type Severity = "high" | "suspicious" | "info";

export type PageInfo = {
  page_number: number;
  width_pt: number;
  height_pt: number;
  rotation: number;
  render_width_px: number | null;
  render_height_px: number | null;
  render_dpi: number | null;
  render_available: boolean;
};

export type Finding = {
  finding_id: string;
  detector_id: string;
  detector_name: string;
  severity: Severity;
  confidence: number;
  page: number;
  bbox: BBox;
  excerpt: string;
  rationale: string;
};

export type SkillEvidence = { span_id: string; page: number; bbox: BBox; text: string };

export type Skill = {
  skill_id: string;
  canonical_name: string;
  confidence: number;
  support_count: number;
  flagged_support_count: number;
  source: string;
  evidence: SkillEvidence[];
};

export type ProcessingState = "uploaded" | "queued" | "processing" | "completed" | "failed";

export type Resume = {
  resume_id: string;
  filename: string;
  state: ProcessingState;
  page_count: number | null;
  byte_size: number;
  failure_code: string | null;
  created_at: string;
  pages: PageInfo[];
  findings_by_severity: { high: number; suspicious: number; info: number };
  skill_count: number;
  evidence_available: boolean;
};

export type ResumeSummary = Pick<
  Resume,
  "resume_id" | "filename" | "state" | "page_count" | "created_at"
>;

export type Identity = {
  user_id: string;
  email: string;
  display_name: string | null;
  onboarded: boolean;
};

export type UploadAccepted = {
  resume_id: string;
  state: ProcessingState;
  filename: string;
  page_count: number;
  duplicate_of_existing: boolean;
};
