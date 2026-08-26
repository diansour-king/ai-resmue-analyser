"use client";

import Link from "next/link";

import type { MatchSummary } from "@/lib/types";

export function MatchList({
  matches,
  emptyMessage = "No match evaluations yet.",
}: {
  matches: MatchSummary[];
  emptyMessage?: string;
}) {
  if (matches.length === 0) {
    return (
      <div
        data-testid="empty-matches"
        className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-lowest p-12 text-center"
      >
        <span className="text-4xl" aria-hidden="true">
          ⚡
        </span>
        <h3 className="mt-4 font-display text-title-lg text-on-surface">{emptyMessage}</h3>
        <p className="mt-1 max-w-md text-body-md text-on-surface-variant">
          Match your verified resume against any job description to evaluate requirements alignment,
          unmet criteria, and tamper risk.
        </p>
        <Link
          href="/app/matches/new"
          className="mt-6 rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary shadow-sm hover:bg-primary/90"
        >
          Evaluate New Match
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col divide-y divide-surface-container overflow-hidden rounded-2xl border border-outline-variant/30 bg-surface-container-lowest shadow-ocean">
      {matches.map((m) => {
        const scoreVal = m.score !== null ? m.score.toFixed(1) : null;
        const deltaVal = m.impact_delta !== null ? m.impact_delta : 0;
        const hasPenalty = deltaVal > 0;

        return (
          <div
            key={m.match_run_id}
            data-testid={`match-row-${m.match_run_id}`}
            className="group flex flex-col justify-between gap-4 p-5 transition-colors hover:bg-surface-container/40 sm:flex-row sm:items-center sm:p-6"
          >
            <div className="flex flex-col gap-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-display text-title-md font-semibold text-on-surface">
                  {m.job.title || "Job Description Match"}
                </span>
                <span
                  className={`rounded-md px-2 py-0.5 text-caption font-medium capitalize ${
                    m.state === "completed"
                      ? "bg-emerald-100 text-emerald-800"
                      : m.state === "failed"
                      ? "bg-rose-100 text-rose-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {m.state}
                </span>
              </div>
              <p className="text-body-sm text-on-surface-variant">
                {m.job.company || "Unknown Company"}{" "}
                {m.job.location ? `• ${m.job.location}` : ""} •{" "}
                {new Date(m.created_at).toLocaleDateString()}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4">
              {/* Score breakdown */}
              {m.state === "completed" && scoreVal !== null && (
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="font-display text-2xl font-bold text-primary">
                      {scoreVal}
                    </span>
                    <span className="text-caption text-on-surface-variant"> / 100</span>
                    {hasPenalty && (
                      <p className="text-[11px] font-semibold text-amber-700">
                        -{deltaVal.toFixed(1)} penalty
                      </p>
                    )}
                  </div>
                </div>
              )}

              <Link
                href={`/app/matches/${m.match_run_id}`}
                className="rounded-lg border border-outline-variant/40 bg-surface px-4 py-2 text-label-md font-semibold text-primary transition-colors hover:bg-surface-container"
              >
                View Match →
              </Link>
            </div>
          </div>
        );
      })}
    </div>
  );
}
