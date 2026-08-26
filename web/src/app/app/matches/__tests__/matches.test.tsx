import { act, render, screen } from "@testing-library/react";
import { Suspense } from "react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";



import MatchResultPage from "../[matchId]/page";
import MatchesPage from "../page";
import { ClaimDetail } from "@/components/ClaimDetail";
import { MatchList } from "@/components/MatchList";
import { RequirementTable } from "@/components/RequirementTable";
import { ScoreCard } from "@/components/ScoreCard";
import { api } from "@/lib/api";
import type { MatchClaim, MatchRun, MatchSummary } from "@/lib/types";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
}));

const mockClaimPython: MatchClaim = {
  claim_id: "claim-1",
  requirement_id: "req-1",
  requirement_text: "5+ years Python in production",
  kind: "hard_skill",
  necessity: "required",
  criticality: 3,
  weight: 3.0,
  met: true,
  match_type: "direct",
  satisfaction: 1.0,
  corroboration: 0.8,
  integrity_factor: 1.0,
  evidence_quality: 0.8,
  contribution: 2.4,
  confidence: 0.98,
  evidence: {
    span_id: "span-1",
    page: 1,
    quote: "Senior Backend Engineer with 6 years Python and FastAPI experience",
    bbox: [72.0, 100.0, 400.0, 120.0],
  },
  all_evidence_spans: ["span-1"],
  findings: [],
  rationale: "Direct match on production Python experience.",
  adjacency_note: null,
};

const mockClaimRedis: MatchClaim = {
  claim_id: "claim-2",
  requirement_id: "req-2",
  requirement_text: "Apache Kafka event streaming",
  kind: "hard_skill",
  necessity: "preferred",
  criticality: 2,
  weight: 2.0,
  met: true,
  match_type: "adjacent",
  satisfaction: 0.8,
  corroboration: 0.5,
  integrity_factor: 0.5, // Flagged by tamper finding
  evidence_quality: 0.7,
  contribution: 0.56,
  confidence: 0.85,
  evidence: {
    span_id: "span-2",
    page: 1,
    quote: "Implemented asynchronous event pipeline using Redis Streams",
    bbox: [72.0, 200.0, 380.0, 215.0],
  },
  all_evidence_spans: ["span-2"],
  findings: [
    {
      finding_id: "find-1",
      detector_id: "D2",
      detector_name: "Low-contrast text",
      severity: "suspicious",
    },
  ],
  rationale: "Candidate has Redis event-streaming rather than Kafka.",
  adjacency_note: "Redis Streams provides comparable publish-subscribe semantics.",
};

const mockClaimUnmet: MatchClaim = {
  claim_id: "claim-3",
  requirement_id: "req-3",
  requirement_text: "AWS Solutions Architect Certification",
  kind: "credential",
  necessity: "preferred",
  criticality: 1,
  weight: 1.0,
  met: false,
  match_type: "none",
  satisfaction: 0.0,
  corroboration: 0.0,
  integrity_factor: 1.0,
  evidence_quality: 0.0,
  contribution: 0.0,
  confidence: 0.99,
  evidence: null,
  all_evidence_spans: [],
  findings: [],
  rationale: "No AWS credentials listed on the resume.",
  adjacency_note: null,
};

const mockMatchRunCompleted: MatchRun = {
  match_run_id: "match-123",
  resume_id: "resume-456",
  job_description_id: "job-789",
  state: "completed",
  model: "claude-sonnet-5",
  scoring_version: "v1",
  prompt_version: "resume_matching_v1",
  score: 60.6,
  score_if_trusted: 82.0,
  impact_delta: 21.4,
  requirement_count: 3,
  unmet_required_count: 0,
  job: {
    job_description_id: "job-789",
    title: "Senior Backend Engineer",
    company: "TechFlow Systems",
    location: "Remote",
  },
  claims: [mockClaimPython, mockClaimRedis, mockClaimUnmet],
  narrative: "Strong backend match with transferable event streaming experience.",
  failure_code: null,
  token_cost_usd: 0.024,
  latency_ms: 3450,
  created_at: "2026-08-26T12:00:00Z",
};

describe("Phase 3G Match UI Tests", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("ScoreCard component", () => {
    it("renders exact API score, score_if_trusted, and impact_delta without client calculation", () => {
      render(<ScoreCard match={mockMatchRunCompleted} />);

      expect(screen.getByTestId("match-score-value")).toHaveTextContent("60.6");
      expect(screen.getByTestId("trusted-score-value")).toHaveTextContent("82.0");
      expect(screen.getByTestId("impact-delta-value")).toHaveTextContent("-21.4");
      expect(screen.getByTestId("unmet-required-count")).toHaveTextContent("0");
    });

    it("refuses to render without unmet_required_count", () => {
      const brokenMatch = {
        ...mockMatchRunCompleted,
        unmet_required_count: null,
      } as unknown as MatchRun;

      render(<ScoreCard match={brokenMatch} />);

      expect(screen.getByRole("alert")).toHaveTextContent(
        /Missing Critical Match Metric/i,
      );
      expect(screen.queryByTestId("match-score-value")).not.toBeInTheDocument();
    });

    it("shows stale-run badge when versions differ", () => {
      render(<ScoreCard match={mockMatchRunCompleted} isStale={true} />);

      expect(screen.getByTestId("stale-run-badge")).toBeInTheDocument();
      expect(screen.getByTestId("stale-run-badge")).toHaveTextContent(
        /Version Stale/i,
      );
    });

    it("displays prominent integrity notice when impact_delta > 0", () => {
      render(<ScoreCard match={mockMatchRunCompleted} />);

      expect(screen.getByRole("region", { name: /integrity impact notice/i })).toBeInTheDocument();
      expect(screen.getByText(/21.4 point penalty applied/i)).toBeInTheDocument();
    });
  });

  describe("RequirementTable component", () => {
    it("renders requirement cards with required/preferred distinction and match types", () => {
      render(<RequirementTable claims={mockMatchRunCompleted.claims} />);

      expect(screen.getByText("5+ years Python in production")).toBeInTheDocument();
      expect(screen.getByText("Apache Kafka event streaming")).toBeInTheDocument();
      expect(screen.getByText("AWS Solutions Architect Certification")).toBeInTheDocument();

      // Necessity badges
      expect(screen.getByTestId(`claim-necessity-${mockClaimPython.claim_id}`)).toHaveTextContent("required");
      expect(screen.getByTestId(`claim-necessity-${mockClaimRedis.claim_id}`)).toHaveTextContent("preferred");

      // Match type badges
      expect(screen.getByTestId(`claim-match-type-${mockClaimPython.claim_id}`)).toHaveTextContent("direct match");
      expect(screen.getByTestId(`claim-match-type-${mockClaimRedis.claim_id}`)).toHaveTextContent("adjacent match");
      expect(screen.getByTestId(`claim-match-type-${mockClaimUnmet.claim_id}`)).toHaveTextContent("none match");
    });

    it("toggles arithmetic scoring formula and displays exact sum alignment", async () => {
      render(<RequirementTable claims={mockMatchRunCompleted.claims} />);

      const toggle = screen.getByTestId("arithmetic-toggle");
      expect(screen.queryByTestId("arithmetic-breakdown")).not.toBeInTheDocument();

      await userEvent.click(toggle);

      expect(screen.getByTestId("arithmetic-breakdown")).toBeInTheDocument();
      expect(screen.getByText(/Deterministic Scoring Formula/i)).toBeInTheDocument();
    });

    it("displays overlapping integrity findings alerts on affected claims", () => {
      render(<RequirementTable claims={mockMatchRunCompleted.claims} />);

      expect(screen.getByTestId(`claim-finding-alert-${mockClaimRedis.claim_id}`)).toBeInTheDocument();
      expect(screen.getByTestId(`claim-finding-alert-${mockClaimRedis.claim_id}`)).toHaveTextContent("1 integrity flag");
    });

    it("handles safely when claim evidence is null", () => {
      render(<RequirementTable claims={[mockClaimUnmet]} />);

      expect(screen.getByText(/No supporting evidence found/i)).toBeInTheDocument();
    });
  });

  describe("ClaimDetail component", () => {
    it("renders full claim rationale, adjacency note, and integrity findings", () => {
      render(<ClaimDetail claim={mockClaimRedis} />);

      expect(screen.getByText("Evaluation Rationale")).toBeInTheDocument();
      expect(screen.getByText(/Candidate has Redis event-streaming/i)).toBeInTheDocument();
      expect(screen.getByText(/Redis Streams provides comparable/i)).toBeInTheDocument();
      expect(screen.getByTestId("claim-findings-section")).toBeInTheDocument();
      expect(screen.getByText("Low-contrast text")).toBeInTheDocument();
    });

    it("displays empty placeholder when no claim is selected", () => {
      render(<ClaimDetail claim={null} />);

      expect(screen.getByText("No Requirement Selected")).toBeInTheDocument();
    });
  });

  describe("MatchList component", () => {
    it("renders list of match summaries and empty state correctly", () => {
      const sampleList: MatchSummary[] = [
        {
          match_run_id: "m-1",
          resume_id: "r-1",
          job_description_id: "j-1",
          state: "completed",
          score: 85.5,
          score_if_trusted: 85.5,
          impact_delta: 0.0,
          requirement_count: 5,
          unmet_required_count: 0,
          job: {
            job_description_id: "j-1",
            title: "Frontend Lead",
            company: "Acme Corp",
            location: "SF",
          },
          created_at: "2026-08-26T10:00:00Z",
          updated_at: "2026-08-26T10:00:00Z",
        },
      ];

      const { rerender } = render(<MatchList matches={sampleList} />);
      expect(screen.getByText("Frontend Lead")).toBeInTheDocument();
      expect(screen.getByText("85.5")).toBeInTheDocument();

      rerender(<MatchList matches={[]} />);
      expect(screen.getByTestId("empty-matches")).toBeInTheDocument();
      expect(screen.getByText("Evaluate New Match")).toBeInTheDocument();
    });
  });

  describe("MatchResultPage full view and SSE handling", () => {
    it("renders completed match without getting stuck in loading", async () => {
      vi.spyOn(api, "getMatch").mockResolvedValue(mockMatchRunCompleted);

      const stableParams = Promise.resolve({ matchId: "match-123" });
      await act(async () => {
        render(
          <Suspense fallback={<p>Loading</p>}>
            <MatchResultPage params={stableParams} />
          </Suspense>,
        );
      });

      const titles = await screen.findAllByText("Senior Backend Engineer");
      expect(titles.length).toBeGreaterThan(0);
      expect(screen.getByTestId("match-score-value")).toHaveTextContent("60.6");
      expect(screen.getAllByText("5+ years Python in production").length).toBeGreaterThan(0);


    });

    it("displays processing state when match is queued or scoring", async () => {
      const processingMatch: MatchRun = {
        ...mockMatchRunCompleted,
        state: "processing",
        score: null,
      };
      vi.spyOn(api, "getMatch").mockResolvedValue(processingMatch);

      const stableParams = Promise.resolve({ matchId: "match-123" });
      await act(async () => {
        render(
          <Suspense fallback={<p>Loading</p>}>
            <MatchResultPage params={stableParams} />
          </Suspense>,
        );
      });

      expect(await screen.findByTestId("match-processing-state")).toBeInTheDocument();
      expect(screen.getByText(/Evaluating Resume Against Job Requirements/i)).toBeInTheDocument();
    });

    it("displays failed state with retry option when match failed", async () => {
      const failedMatch: MatchRun = {
        ...mockMatchRunCompleted,
        state: "failed",
        score: null,
        failure_code: "schema_violation",
      };
      vi.spyOn(api, "getMatch").mockResolvedValue(failedMatch);

      const stableParams = Promise.resolve({ matchId: "match-123" });
      await act(async () => {
        render(
          <Suspense fallback={<p>Loading</p>}>
            <MatchResultPage params={stableParams} />
          </Suspense>,
        );
      });

      expect(await screen.findByTestId("match-failed-state")).toBeInTheDocument();
      expect(screen.getByText(/Reason code: schema_violation/i)).toBeInTheDocument();
      expect(screen.getByText("Retry Evaluation")).toBeInTheDocument();
    });
  });



  describe("MatchesPage overview", () => {
    it("loads and displays user matches", async () => {
      vi.spyOn(api, "listMatches").mockResolvedValue({
        items: [
          {
            match_run_id: "m-1",
            resume_id: "r-1",
            job_description_id: "j-1",
            state: "completed",
            score: 92.0,
            score_if_trusted: 92.0,
            impact_delta: 0.0,
            requirement_count: 4,
            unmet_required_count: 0,
            job: {
              job_description_id: "j-1",
              title: "Senior Python Architect",
              company: "FinTech Global",
              location: "Remote",
            },
            created_at: "2026-08-26T12:00:00Z",
            updated_at: "2026-08-26T12:00:00Z",
          },
        ],
        next_cursor: null,
      });

      render(<MatchesPage />);

      expect(await screen.findByText("Senior Python Architect")).toBeInTheDocument();
      expect(screen.getByText("92.0")).toBeInTheDocument();
    });
  });
});
