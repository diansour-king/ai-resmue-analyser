"use client";

import { useMemo, useState } from "react";

import type { MatchClaim } from "@/lib/types";

export function RequirementTable({
  claims,
  selectedClaimId,
  onSelectClaim,
  onViewEvidence,
}: {
  claims: MatchClaim[];
  selectedClaimId?: string | null;
  onSelectClaim?: (claim: MatchClaim) => void;
  onViewEvidence?: (claim: MatchClaim) => void;
}) {
  const [showArithmetic, setShowArithmetic] = useState(false);
  const [filterNecessity, setFilterNecessity] = useState<"all" | "required" | "preferred">("all");

  const filteredClaims = useMemo(() => {
    return claims.filter((c) => {
      if (filterNecessity !== "all" && c.necessity !== filterNecessity) return false;
      return true;
    });
  }, [claims, filterNecessity]);


  // Compute arithmetic sums from displayed claim fields
  const { totalWeight, totalContribution, computedScore } = useMemo(() => {
    let weightSum = 0;
    let contribSum = 0;
    for (const c of claims) {
      weightSum += c.weight;
      contribSum += c.contribution;
    }
    const score = weightSum > 0 ? (contribSum / weightSum) * 100 : 0;
    return {
      totalWeight: weightSum,
      totalContribution: contribSum,
      computedScore: score,
    };
  }, [claims]);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean">
      {/* Controls: Filters and Arithmetic Breakdown Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-container pb-4">
        <div>
          <h3 className="font-display text-headline-md text-on-surface">
            Requirements Breakdown
          </h3>
          <p className="text-caption text-on-surface-variant">
            {claims.length} discrete requirements evaluated against verified resume evidence
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Necessity Filter */}
          <div className="flex rounded-lg border border-outline-variant/30 bg-surface p-1 text-label-sm">
            <button
              type="button"
              onClick={() => setFilterNecessity("all")}
              className={`rounded-md px-2.5 py-1 transition-colors ${
                filterNecessity === "all"
                  ? "bg-primary text-on-primary font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              All ({claims.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterNecessity("required")}
              className={`rounded-md px-2.5 py-1 transition-colors ${
                filterNecessity === "required"
                  ? "bg-primary text-on-primary font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Required ({claims.filter((c) => c.necessity === "required").length})
            </button>
            <button
              type="button"
              onClick={() => setFilterNecessity("preferred")}
              className={`rounded-md px-2.5 py-1 transition-colors ${
                filterNecessity === "preferred"
                  ? "bg-primary text-on-primary font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Preferred ({claims.filter((c) => c.necessity === "preferred").length})
            </button>
          </div>

          {/* Arithmetic Toggle */}
          <button
            type="button"
            data-testid="arithmetic-toggle"
            onClick={() => setShowArithmetic((prev) => !prev)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-label-sm font-medium transition-colors ${
              showArithmetic
                ? "border-primary bg-secondary-container text-on-secondary-container"
                : "border-outline-variant/40 bg-surface text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            <span aria-hidden="true">∑</span>
            {showArithmetic ? "Hide Scoring Math" : "Show Scoring Math"}
          </button>
        </div>
      </div>

      {/* Arithmetic Explanation Banner if toggled on */}
      {showArithmetic && (
        <div
          data-testid="arithmetic-breakdown"
          className="rounded-xl border border-secondary/30 bg-secondary-container/50 p-4 text-body-sm text-on-secondary-container"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 font-semibold">
            <span>Deterministic Scoring Formula: Score = (∑ Contribution / ∑ Weight) × 100</span>
            <span className="rounded bg-surface px-2 py-0.5 font-mono text-primary">
              ({totalContribution.toFixed(2)} / {totalWeight.toFixed(2)}) × 100 ={" "}
              {computedScore.toFixed(1)}%
            </span>
          </div>
          <p className="mt-1 text-caption text-on-surface-variant">
            Each requirement contribution = Weight × Satisfaction × Match Multiplier × Integrity Factor × Evidence Quality.
          </p>
        </div>
      )}

      {/* Claims List */}
      <div className="flex flex-col divide-y divide-surface-container">
        {filteredClaims.map((claim) => {
          const isSelected = claim.claim_id === selectedClaimId;
          const hasFindings = claim.findings && claim.findings.length > 0;

          return (
            <div
              key={claim.claim_id}
              data-testid={`claim-row-${claim.claim_id}`}
              onClick={() => onSelectClaim?.(claim)}
              className={`group flex flex-col gap-3 p-4 transition-colors sm:p-5 ${
                isSelected
                  ? "bg-secondary-container/40 border-l-4 border-l-primary"
                  : "hover:bg-surface-container-lowest/80"
              }`}
            >
              {/* Top Row: Badges & Met Status */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  {/* Met / Unmet badge */}
                  <span
                    data-testid={`claim-met-${claim.claim_id}`}
                    className={`inline-flex items-center gap-1 rounded-md px-2.5 py-0.5 text-label-sm font-semibold ${
                      claim.met
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {claim.met ? "✓ Met" : "✕ Unmet"}
                  </span>

                  {/* Match Type Badge */}
                  <span
                    data-testid={`claim-match-type-${claim.claim_id}`}
                    className="rounded-md bg-surface-container px-2 py-0.5 text-caption font-medium capitalize text-on-surface-variant"
                  >
                    {claim.match_type} match
                  </span>

                  {/* Necessity */}
                  <span
                    data-testid={`claim-necessity-${claim.claim_id}`}
                    className={`rounded-md px-2 py-0.5 text-caption font-medium uppercase tracking-wider ${
                      claim.necessity === "required"
                        ? "bg-slate-200 text-slate-800"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {claim.necessity}
                  </span>

                  {/* Kind */}
                  <span className="rounded-md border border-outline-variant/30 px-2 py-0.5 text-caption text-on-surface-variant">
                    {claim.kind.replace("_", " ")}
                  </span>

                  {/* Criticality */}
                  <span className="text-caption text-on-surface-variant">
                    Priority: {claim.criticality}/3
                  </span>
                </div>

                {/* Overlapping Findings Alert Badge */}
                {hasFindings && (
                  <span
                    data-testid={`claim-finding-alert-${claim.claim_id}`}
                    className="inline-flex items-center gap-1 rounded-md bg-amber-100 px-2.5 py-0.5 text-caption font-semibold text-amber-900"
                  >
                    ⚠ {claim.findings.length} integrity {claim.findings.length === 1 ? "flag" : "flags"}
                  </span>
                )}
              </div>

              {/* Requirement Text */}
              <p className="text-body-md font-medium text-on-surface">
                {claim.requirement_text}
              </p>

              {/* Arithmetic Breakdown (visible when toggled) */}
              {showArithmetic && (
                <div className="grid grid-cols-2 gap-2 rounded-lg bg-surface p-3 font-mono text-caption text-on-surface-variant sm:grid-cols-6">
                  <div>
                    <span className="block text-[10px] uppercase text-on-surface-variant">Weight</span>
                    <span className="font-semibold text-on-surface">{claim.weight.toFixed(1)}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-on-surface-variant">Satisfaction</span>
                    <span className="font-semibold text-on-surface">{claim.satisfaction.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-on-surface-variant">Corroboration</span>
                    <span className="font-semibold text-on-surface">{claim.corroboration.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-on-surface-variant">Integrity</span>
                    <span className={`font-semibold ${claim.integrity_factor < 1 ? "text-amber-700" : "text-on-surface"}`}>
                      {claim.integrity_factor.toFixed(2)}
                    </span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-on-surface-variant">Quality</span>
                    <span className="font-semibold text-on-surface">{claim.evidence_quality.toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="block text-[10px] uppercase text-primary font-bold">Contribution</span>
                    <span className="font-bold text-primary">{claim.contribution.toFixed(2)} pts</span>
                  </div>
                </div>
              )}

              {/* Cited Evidence & Rationale Preview */}
              {claim.evidence ? (
                <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-outline-variant/20 bg-surface-container/50 px-3 py-2 text-body-sm">
                  <div className="flex items-center gap-2 overflow-hidden text-on-surface-variant">
                    <span className="font-semibold text-secondary">p.{claim.evidence.page}:</span>
                    <span className="truncate italic">&ldquo;{claim.evidence.quote}&rdquo;</span>
                  </div>


                  {onViewEvidence && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewEvidence(claim);
                      }}
                      className="ml-auto inline-flex items-center gap-1 text-label-sm font-semibold text-primary hover:underline"
                    >
                      View on Document →
                    </button>
                  )}
                </div>
              ) : (
                <p className="text-caption italic text-on-surface-variant">
                  No supporting evidence found in resume.
                </p>
              )}

              {/* Adjacency Note if present */}
              {claim.adjacency_note && (
                <p className="text-caption text-secondary">
                  <span className="font-semibold">Transferable rationale:</span> {claim.adjacency_note}
                </p>
              )}
            </div>
          );
        })}

        {filteredClaims.length === 0 && (
          <div className="p-8 text-center text-body-md text-on-surface-variant">
            No requirements match the selected filters.
          </div>
        )}
      </div>
    </div>
  );
}
