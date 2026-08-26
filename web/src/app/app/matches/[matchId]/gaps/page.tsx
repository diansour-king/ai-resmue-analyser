"use client";

import Link from "next/link";
import { Suspense, use, useCallback, useEffect, useMemo, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { GapList } from "@/components/GapList";
import { api } from "@/lib/api";
import type { GapAnalysisResponse, MatchRun } from "@/lib/types";

function MatchGapsContent({ matchId }: { matchId: string }) {
  const [match, setMatch] = useState<MatchRun | null>(null);
  const [gapsData, setGapsData] = useState<GapAnalysisResponse | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());

  const load = useCallback(() => {
    setError(null);
    Promise.all([api.getMatch(matchId), api.getMatchGaps(matchId)])
      .then(([m, g]) => {
        setMatch(m);
        setGapsData(g);
      })
      .catch(setError);
  }, [matchId]);

  useEffect(load, [load]);

  const handleToggleSkill = (skill: string) => {
    setSelectedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skill)) {
        next.delete(skill);
      } else {
        next.add(skill);
      }
      return next;
    });
  };

  // Lookup the exact server-projected score from precomputed combinations
  const currentProjectedScore = useMemo(() => {
    if (!gapsData) return 0;
    if (selectedSkills.size === 0) {
      return gapsData.base_score;
    }

    const selectedList = Array.from(selectedSkills).sort();

    // If single skill selected, look up candidate's projected_score
    if (selectedList.length === 1) {
      const single = gapsData.candidates.find((c) => c.skill === selectedList[0]);
      if (single) return single.projected_score;
    }

    // If multiple skills selected, look up precomputed combination
    const matchingCombo = gapsData.combinations.find(
      (combo) =>
        combo.skills.length === selectedList.length &&
        combo.skills.every((s, i) => s === selectedList[i]),
    );

    if (matchingCombo) {
      return matchingCombo.projected_score;
    }

    // Fallback if combination not precomputed
    return gapsData.base_score;
  }, [gapsData, selectedSkills]);

  const baseScore = gapsData?.base_score ?? 0;
  const scoreDelta = currentProjectedScore - baseScore;

  return (
    <AsyncState loading={(!match || !gapsData) && !error} error={error} onRetry={load}>
      {match && gapsData && (
        <div className="flex flex-col gap-6">
          {/* Breadcrumb Header */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-body-md text-secondary">
              <Link href="/app/matches" className="hover:text-primary">
                Match Evaluations
              </Link>
              <span aria-hidden="true">›</span>
              <Link href={`/app/matches/${matchId}`} className="hover:text-primary">
                {match.job.title || "Match Result"}
              </Link>
              <span aria-hidden="true">›</span>
              <span className="font-semibold text-on-surface">Skill Gap Simulator</span>
            </div>

            <Link
              href={`/app/matches/${matchId}`}
              className="rounded-lg border border-outline-variant/40 px-3 py-1.5 text-label-sm font-medium text-on-surface-variant hover:bg-surface-container"
            >
              ← Back to Match Overview
            </Link>
          </div>

          {/* Top Score Simulator Card */}
          <div className="flex flex-col gap-6 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
                  Counterfactual Simulation
                </span>
                <h1 className="font-display text-headline-lg text-on-surface">
                  {match.job.title || "Job Target"} Skill Gaps
                </h1>
                {match.job.company && (
                  <p className="text-body-md text-on-surface-variant">
                    {match.job.company} • Deterministic Uplift Projection
                  </p>
                )}
              </div>

              {/* Server Projection Badge */}
              <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-secondary-container px-3 py-1 text-label-sm font-semibold text-on-secondary-container">
                <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
                Server-Projected Scoring
              </span>
            </div>

            {/* Gauge / Score Metrics Grid */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {/* Base Score */}
              <div className="flex flex-col justify-between rounded-xl border border-surface-container-high bg-surface-container p-5">
                <p className="text-caption text-on-surface-variant">Current Verified Score</p>
                <div className="mt-2 flex items-baseline gap-1">
                  <span
                    data-testid="base-match-score"
                    className="font-display text-4xl font-bold text-on-surface"
                  >
                    {baseScore.toFixed(1)}
                  </span>
                  <span className="text-label-md text-on-surface-variant">/ 100</span>
                </div>
                <p className="mt-2 text-caption text-on-surface-variant">
                  Current match before hypothetical skills
                </p>
              </div>

              {/* Projected Score */}
              <div className="flex flex-col justify-between rounded-xl border border-primary/20 bg-secondary-container/40 p-5">
                <p className="text-caption font-semibold text-primary">Simulated Projected Score</p>
                <div className="mt-2 flex items-baseline gap-1">
                  <span
                    data-testid="projected-match-score"
                    className="font-display text-4xl font-bold text-primary"
                  >
                    {currentProjectedScore.toFixed(1)}
                  </span>
                  <span className="text-label-md text-on-surface-variant">/ 100</span>
                </div>
                <p className="mt-2 text-caption text-on-surface-variant">
                  Hypothetical score with selected clean evidence
                </p>
              </div>

              {/* Score Uplift */}
              <div className="flex flex-col justify-between rounded-xl border border-surface-container-high bg-surface-container p-5">
                <p className="text-caption text-on-surface-variant">Projected Uplift</p>
                <div className="mt-2 flex items-baseline gap-1">
                  <span
                    data-testid="projected-score-delta"
                    className={`font-display text-4xl font-bold ${
                      scoreDelta > 0 ? "text-emerald-700" : "text-on-surface"
                    }`}
                  >
                    {scoreDelta > 0 ? `+${scoreDelta.toFixed(1)}` : "0.0"}
                  </span>
                  <span className="text-label-md text-on-surface-variant">pts</span>
                </div>
                <p className="mt-2 text-caption text-on-surface-variant">
                  {selectedSkills.size > 0
                    ? `From ${selectedSkills.size} selected ${
                        selectedSkills.size === 1 ? "skill" : "skills"
                      }`
                    : "Select skills below to simulate"}
                </p>
              </div>
            </div>
          </div>

          {/* Interactive Gap List */}
          <GapList
            candidates={gapsData.candidates}
            gaps={gapsData.gaps}
            selectedSkills={selectedSkills}
            onToggleSkill={handleToggleSkill}
          />
        </div>
      )}
    </AsyncState>
  );
}

export default function MatchGapsPage({
  params,
}: {
  params: Promise<{ matchId: string }>;
}) {
  const { matchId } = use(params);

  return (
    <Suspense fallback={<div className="p-8 text-body-md">Loading Skill Gaps...</div>}>
      <MatchGapsContent matchId={matchId} />
    </Suspense>
  );
}
