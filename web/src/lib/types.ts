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

export type MatchAccepted = {
  match_run_id: string;
  state: string;
  resume_id: string;
  job_description_id: string;
  reused: boolean;
  duplicate_of_existing: boolean;
};

export type MatchJobSummary = {
  job_description_id: string;
  title: string | null;
  company: string | null;
  location: string | null;
};

export type MatchSummary = {
  match_run_id: string;
  resume_id: string;
  job_description_id: string;
  state: string;
  score: number | null;
  score_if_trusted: number | null;
  impact_delta: number | null;
  requirement_count: number | null;
  unmet_required_count: number | null;
  job: MatchJobSummary;
  created_at: string;
  updated_at: string;
};

export type ClaimEvidenceDetail = {
  span_id: string;
  page: number;
  quote: string;
  bbox: [number, number, number, number] | null;
};

export type ClaimFindingDetail = {
  finding_id: string;
  detector_id: string;
  detector_name: string | null;
  severity: Severity;
};

export type MatchClaim = {
  claim_id: string;
  requirement_id: string;
  requirement_text: string;
  kind: string;
  necessity: string;
  criticality: number;
  weight: number;
  met: boolean;
  match_type: "direct" | "adjacent" | "none";
  satisfaction: number;
  corroboration: number;
  integrity_factor: number;
  evidence_quality: number;
  contribution: number;
  confidence: number;
  evidence: ClaimEvidenceDetail | null;
  all_evidence_spans: string[];
  findings: ClaimFindingDetail[];
  rationale: string | null;
  adjacency_note: string | null;
};

export type MatchRun = {
  match_run_id: string;
  resume_id: string;
  job_description_id: string;
  state: string;
  model: string;
  scoring_version: string;
  prompt_version: string | null;
  score: number | null;
  score_if_trusted: number | null;
  impact_delta: number | null;
  requirement_count: number | null;
  unmet_required_count: number | null;
  job: MatchJobSummary;
  claims: MatchClaim[];
  narrative: string | null;
  failure_code: string | null;
  token_cost_usd: number | null;
  latency_ms: number | null;
  created_at: string;
};

export type JobRequirementEvidence = {

  start: number;
  end: number;
  quote: string;
};

export type JobRequirement = {
  requirement_id: string;
  ordinal: number;
  text: string;
  kind: string;
  necessity: string;
  criticality: number;
  weight: number;
  evidence: JobRequirementEvidence;
};

export type JobAccepted = {
  job_description_id: string;
  state: ProcessingState;
  source: string;
  title: string | null;
  company: string | null;
  sha256: string;
  duplicate_of_existing: boolean;
};

export type JobSummary = {
  job_description_id: string;
  title: string | null;
  company: string | null;
  location: string | null;
  source: string;
  state: ProcessingState;
  created_at: string;
};

export type JobDescription = {
  job_description_id: string;
  title: string | null;
  company: string | null;
  location: string | null;
  source: string;
  state: ProcessingState;
  raw_text: string | null;
  normalized_text: string | null;
  sha256: string;
  page_count: number | null;
  failure_code: string | null;
  extractor_version: string | null;
  is_fixture: boolean;
  created_at: string;
  updated_at: string;
  requirement_count: number;
  findings_by_severity: { high: number; suspicious: number; info: number };
};

export type GapCategory = "missing" | "partial" | "unverifiable";

export type GapItem = {
  requirement_id: string;
  skill: string;
  category: GapCategory;
  requirement_text: string;
  necessity: string;
  criticality: number;
  weight: number;
  current_satisfaction: number;
  current_evidence_quality: number;
  current_contribution: number;
  points_available: number;
  projected_score: number;
};

export type CandidateSkillGap = {
  skill: string;
  category: GapCategory;
  requirement_ids: string[];
  points_available: number;
  projected_score: number;
};

export type SkillCombinationProjection = {
  skills: string[];
  projected_score: number;
};

export type GapAnalysisResponse = {
  match_run_id: string;
  base_score: number;
  base_score_if_trusted: number;
  impact_delta: number;
  unmet_required_count: number;
  gaps: GapItem[];
  candidates: CandidateSkillGap[];
  combinations: SkillCombinationProjection[];
  request_id?: string | null;
};



