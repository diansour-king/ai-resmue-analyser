"use client";

import type { MatchRun } from "@/lib/types";

/**
 * The primary Score Card for Match Results.
 *
 * Displays:
 * 1. Score: The final deterministic match score computed by the scoring engine (0-100).
 * 2. Score If Trusted: The hypothetical score if all evidence was clean and untampered.
 * 3. Impact Delta: The reduction in score caused by untrusted/suspicious evidence findings.
 * 4. Requirement counts and unmet mandatory requirements.
 *
 * Strictly adheres to the product rule: The score card refuses to render without
 * unmet_required_count, as a score without knowing if hard bars were missed is misleading.
 */
export function ScoreCard({
  match,
  isStale = false,
}: {
  match: MatchRun;
  isStale?: boolean;
}) {
  if (
    match.unmet_required_count === null ||
    match.unmet_required_count === undefined
  ) {
    return (
      <div
        role="alert"
        className="rounded-xl border border-error/30 bg-error/10 p-6 text-on-surface"
      >
        <p className="font-semibold text-error">Missing Critical Match Metric</p>
        <p className="mt-1 text-body-sm text-on-surface-variant">
          Score card cannot be displayed without verified unmet requirement data.
        </p>
      </div>
    );
  }

  const scoreVal = match.score !== null && match.score !== undefined ? match.score : null;
  const trustedVal =
    match.score_if_trusted !== null && match.score_if_trusted !== undefined
      ? match.score_if_trusted
      : null;
  const deltaVal =
    match.impact_delta !== null && match.impact_delta !== undefined
      ? match.impact_delta
      : 0;

  const hasImpactPenalty = deltaVal > 0;
  const hasUnmetRequired = match.unmet_required_count > 0;

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean sm:p-8">
      {/* Header with Title & Stale Badge */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
            Deterministic Match Evaluation
          </span>
          <h2 className="font-display text-headline-lg text-on-surface">
            {match.job.title || "Job Match Evaluation"}
          </h2>
          {match.job.company && (
            <p className="text-body-md text-on-surface-variant">
              {match.job.company} {match.job.location ? `• ${match.job.location}` : ""}
            </p>
          )}
        </div>

        {isStale && (
          <span
            data-testid="stale-run-badge"
            className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-label-sm font-medium text-amber-800"
          >
            <span className="h-2 w-2 rounded-full bg-amber-500" aria-hidden="true" />
            Prompt/Scoring Version Stale
          </span>
        )}
      </div>

      {/* Main KPI Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Final Match Score */}
        <div className="flex flex-col justify-between rounded-xl border border-surface-container-high bg-surface-container p-5">
          <p className="text-caption text-on-surface-variant">Final Match Score</p>
          <div className="mt-2 flex items-baseline gap-1">
            <span
              data-testid="match-score-value"
              className="font-display text-4xl font-bold tracking-tight text-primary"
            >
              {scoreVal !== null ? scoreVal.toFixed(1) : "—"}
            </span>
            <span className="text-label-md text-on-surface-variant">/ 100</span>
          </div>
          <p className="mt-2 text-caption text-on-surface-variant">
            Deterministic weighted evidence score
          </p>
        </div>

        {/* Score If Trusted */}
        <div className="flex flex-col justify-between rounded-xl border border-surface-container-high bg-surface-container p-5">
          <p className="text-caption text-on-surface-variant">Score If Trusted</p>
          <div className="mt-2 flex items-baseline gap-1">
            <span
              data-testid="trusted-score-value"
              className="font-display text-3xl font-bold text-on-surface"
            >
              {trustedVal !== null ? trustedVal.toFixed(1) : "—"}
            </span>
            <span className="text-label-md text-on-surface-variant">/ 100</span>
          </div>
          <p className="mt-2 text-caption text-on-surface-variant">
            Score assuming zero tamper findings
          </p>
        </div>

        {/* Integrity Impact Delta */}
        <div
          className={`flex flex-col justify-between rounded-xl border p-5 ${
            hasImpactPenalty
              ? "border-amber-200 bg-amber-50/50"
              : "border-surface-container-high bg-surface-container"
          }`}
        >
          <p className="text-caption text-on-surface-variant">Integrity Impact Delta</p>
          <div className="mt-2 flex items-baseline gap-1">
            <span
              data-testid="impact-delta-value"
              className={`font-display text-3xl font-bold ${
                hasImpactPenalty ? "text-amber-700" : "text-on-surface"
              }`}
            >
              {deltaVal > 0 ? `-${deltaVal.toFixed(1)}` : "0.0"}
            </span>
            <span className="text-label-md text-on-surface-variant">pts</span>
          </div>
          <p className="mt-2 text-caption text-on-surface-variant">
            {hasImpactPenalty
              ? "Evidence discounted due to findings"
              : "Zero penalty — evidence clean"}
          </p>
        </div>

        {/* Requirements & Unmet Required */}
        <div
          className={`flex flex-col justify-between rounded-xl border p-5 ${
            hasUnmetRequired
              ? "border-error/20 bg-error/5"
              : "border-surface-container-high bg-surface-container"
          }`}
        >
          <p className="text-caption text-on-surface-variant">Requirements Bar</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              data-testid="unmet-required-count"
              className={`font-display text-3xl font-bold ${
                hasUnmetRequired ? "text-error" : "text-secondary"
              }`}
            >
              {match.unmet_required_count}
            </span>
            <span className="text-label-sm text-on-surface-variant">
              unmet required / {match.requirement_count ?? match.claims.length} total
            </span>
          </div>
          <p className="mt-2 text-caption text-on-surface-variant">
            {hasUnmetRequired
              ? "Missing non-negotiable criteria"
              : "All mandatory criteria satisfied"}
          </p>
        </div>
      </div>

      {/* Integrity Impact Notice Callout if penalty exists */}
      {hasImpactPenalty && (
        <div
          role="region"
          aria-label="Integrity impact notice"
          className="flex items-start gap-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900"
        >
          <span className="text-xl" aria-hidden="true">
            ⚠
          </span>
          <div className="flex-1 text-body-sm">
            <p className="font-semibold text-amber-950">
              Evidence Integrity Notice: {deltaVal.toFixed(1)} point penalty applied
            </p>
            <p className="mt-0.5 text-amber-900">
              One or more claims cite resume sections with active integrity findings (e.g.
              hidden text or visual anomalies). The score reflects discounted contribution to
              prevent fabricated qualifications from distorting evaluation.
            </p>
          </div>
        </div>
      )}

      {/* Narrative rationale if present */}
      {match.narrative && (
        <div className="rounded-xl border border-outline-variant/20 bg-surface/60 p-5">
          <p className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
            Evaluation Narrative
          </p>
          <p className="mt-2 text-body-md text-on-surface-variant leading-relaxed">
            {match.narrative}
          </p>
        </div>
      )}
    </div>
  );
}
