import { act, render, screen } from "@testing-library/react";
import { Suspense } from "react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import MatchGapsPage from "../[matchId]/gaps/page";
import { GapList } from "@/components/GapList";
import { api } from "@/lib/api";
import type { GapAnalysisResponse, MatchRun } from "@/lib/types";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockMatchRun: MatchRun = {
  match_run_id: "m-123",
  resume_id: "r-456",
  job_description_id: "j-789",
  state: "completed",
  model: "claude-sonnet-5",
  scoring_version: "v1",
  prompt_version: "resume_matching_v1",
  score: 60.6,
  score_if_trusted: 82.0,
  impact_delta: 21.4,
  requirement_count: 3,
  unmet_required_count: 1,
  job: {
    job_description_id: "j-789",
    title: "Senior Backend Engineer",
    company: "TechFlow Systems",
    location: "Remote",
  },
  claims: [],
  narrative: "Match summary",
  failure_code: null,
  token_cost_usd: 0.02,
  latency_ms: 3000,
  created_at: "2026-08-26T12:00:00Z",
};

const mockGapsResponse: GapAnalysisResponse = {
  match_run_id: "m-123",
  base_score: 60.6,
  base_score_if_trusted: 82.0,
  impact_delta: 21.4,
  unmet_required_count: 1,
  gaps: [
    {
      requirement_id: "req-k8s",
      skill: "Kubernetes",
      category: "missing",
      requirement_text: "Kubernetes cluster administration",
      necessity: "required",
      criticality: 3,
      weight: 3.0,
      current_satisfaction: 0.0,
      current_evidence_quality: 0.0,
      current_contribution: 0.0,
      points_available: 3.0,
      projected_score: 75.0,
    },
    {
      requirement_id: "req-kafka",
      skill: "Kafka",
      category: "partial",
      requirement_text: "Apache Kafka event streaming",
      necessity: "preferred",
      criticality: 2,
      weight: 2.0,
      current_satisfaction: 0.6,
      current_evidence_quality: 0.8,
      current_contribution: 0.96,
      points_available: 1.04,
      projected_score: 65.0,
    },
    {
      requirement_id: "req-aws",
      skill: "AWS",
      category: "unverifiable",
      requirement_text: "AWS Solutions Architect",
      necessity: "required",
      criticality: 3,
      weight: 3.0,
      current_satisfaction: 1.0,
      current_evidence_quality: 0.0,
      current_contribution: 0.0,
      points_available: 3.0,
      projected_score: 82.0,
    },
  ],
  candidates: [
    {
      skill: "Kubernetes",
      category: "missing",
      requirement_ids: ["req-k8s"],
      points_available: 3.0,
      projected_score: 75.0,
    },
    {
      skill: "AWS",
      category: "unverifiable",
      requirement_ids: ["req-aws"],
      points_available: 3.0,
      projected_score: 82.0,
    },
    {
      skill: "Kafka",
      category: "partial",
      requirement_ids: ["req-kafka"],
      points_available: 1.04,
      projected_score: 65.0,
    },
  ],
  combinations: [
    {
      skills: ["AWS", "Kubernetes"],
      projected_score: 88.0, // Non-additive: server projected score
    },
    {
      skills: ["Kafka", "Kubernetes"],
      projected_score: 79.0,
    },
    {
      skills: ["AWS", "Kafka"],
      projected_score: 85.0,
    },
    {
      skills: ["AWS", "Kafka", "Kubernetes"],
      projected_score: 94.0,
    },
  ],
};

describe("Phase 3H Skill Gap UI Tests", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("GapList component", () => {
    it("renders all candidates and requirement gaps with correct category badges", () => {
      render(
        <GapList
          candidates={mockGapsResponse.candidates}
          gaps={mockGapsResponse.gaps}
          selectedSkills={new Set()}
          onToggleSkill={() => {}}
        />,
      );

      expect(screen.getByText("Kubernetes")).toBeInTheDocument();
      expect(screen.getAllByText("Missing Evidence").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Partial Match").length).toBeGreaterThan(0);
      expect(screen.getAllByText("Unverifiable").length).toBeGreaterThan(0);
    });


    it("renders empty state when no gaps exist", () => {
      render(
        <GapList
          candidates={[]}
          gaps={[]}
          selectedSkills={new Set()}
          onToggleSkill={() => {}}
        />,
      );

      expect(screen.getByTestId("empty-gaps")).toBeInTheDocument();
      expect(screen.getByText("No Skill Gaps Identified")).toBeInTheDocument();
    });
  });

  describe("MatchGapsPage counterfactual simulation", () => {
    it("displays base score when no skills are selected", async () => {
      vi.spyOn(api, "getMatch").mockResolvedValue(mockMatchRun);
      vi.spyOn(api, "getMatchGaps").mockResolvedValue(mockGapsResponse);

      const stableParams = Promise.resolve({ matchId: "m-123" });
      await act(async () => {
        render(
          <Suspense fallback={<p>Loading</p>}>
            <MatchGapsPage params={stableParams} />
          </Suspense>,
        );
      });

      expect(await screen.findByTestId("base-match-score")).toHaveTextContent("60.6");
      expect(screen.getByTestId("projected-match-score")).toHaveTextContent("60.6");
      expect(screen.getByTestId("projected-score-delta")).toHaveTextContent("0.0");
    });

    it("updates to exact server projection on single and combination skill toggles", async () => {
      vi.spyOn(api, "getMatch").mockResolvedValue(mockMatchRun);
      vi.spyOn(api, "getMatchGaps").mockResolvedValue(mockGapsResponse);

      const stableParams = Promise.resolve({ matchId: "m-123" });
      await act(async () => {
        render(
          <Suspense fallback={<p>Loading</p>}>
            <MatchGapsPage params={stableParams} />
          </Suspense>,
        );
      });

      await screen.findByTestId("base-match-score");

      // 1. Toggle Kubernetes -> projected score becomes 75.0 (from server, not 60.6 + 3.0)
      const k8sCheckbox = screen.getByLabelText("Toggle Kubernetes");
      await userEvent.click(k8sCheckbox);

      expect(screen.getByTestId("projected-match-score")).toHaveTextContent("75.0");
      expect(screen.getByTestId("projected-score-delta")).toHaveTextContent("+14.4");

      // 2. Also toggle AWS -> combination ["AWS", "Kubernetes"] projected score becomes 88.0
      const awsCheckbox = screen.getByLabelText("Toggle AWS");
      await userEvent.click(awsCheckbox);

      expect(screen.getByTestId("projected-match-score")).toHaveTextContent("88.0");
      expect(screen.getByTestId("projected-score-delta")).toHaveTextContent("+27.4");
    });
  });
});
