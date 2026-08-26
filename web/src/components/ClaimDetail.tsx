"use client";

import { SeverityChip } from "@/components/SeverityChip";
import type { MatchClaim } from "@/lib/types";

export function ClaimDetail({
  claim,
  onViewOnDocument,
}: {
  claim: MatchClaim | null;
  onViewOnDocument?: (claim: MatchClaim) => void;
}) {
  if (!claim) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant/50 p-8 text-center text-on-surface-variant">
        <span className="text-3xl" aria-hidden="true">
          📋
        </span>
        <p className="mt-3 font-display text-title-md text-on-surface">No Requirement Selected</p>
        <p className="mt-1 max-w-sm text-caption">
          Select any requirement from the list to inspect verified citations, model rationale, and
          tamper integrity flags.
        </p>
      </div>
    );
  }

  const hasFindings = claim.findings && claim.findings.length > 0;

  return (
    <div
      data-testid="claim-detail-panel"
      className="flex flex-col gap-6 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean"
    >
      {/* Header & Badges */}
      <div className="flex flex-col gap-2 border-b border-surface-container pb-4">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 rounded-md px-2.5 py-0.5 text-label-sm font-semibold ${
              claim.met ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
            }`}
          >
            {claim.met ? "✓ Met" : "✕ Unmet"}
          </span>
          <span className="rounded-md bg-surface-container px-2 py-0.5 text-caption font-medium capitalize text-on-surface-variant">
            {claim.match_type} match
          </span>
          <span
            className={`rounded-md px-2 py-0.5 text-caption font-medium uppercase tracking-wider ${
              claim.necessity === "required"
                ? "bg-slate-200 text-slate-800"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            {claim.necessity}
          </span>
          <span className="rounded-md border border-outline-variant/30 px-2 py-0.5 text-caption text-on-surface-variant">
            {claim.kind.replace("_", " ")}
          </span>
          <span className="text-caption text-on-surface-variant">
            Criticality: {claim.criticality}/3
          </span>
        </div>

        <h3 className="mt-1 font-display text-title-lg text-on-surface">
          {claim.requirement_text}
        </h3>
      </div>

      {/* Model Rationale */}
      {claim.rationale && (
        <div className="flex flex-col gap-1">
          <h4 className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
            Evaluation Rationale
          </h4>
          <p className="text-body-md text-on-surface-variant leading-relaxed">{claim.rationale}</p>
        </div>
      )}

      {/* Adjacency Note */}
      {claim.adjacency_note && (
        <div className="flex flex-col gap-1 rounded-xl border border-secondary/20 bg-secondary-container/30 p-4">
          <h4 className="text-label-sm font-semibold text-on-secondary-container">
            Transferable Skill / Adjacency Note
          </h4>
          <p className="mt-1 text-body-sm text-on-secondary-container/90 leading-relaxed">
            {claim.adjacency_note}
          </p>
        </div>
      )}

      {/* Cited Evidence from Resume */}
      <div className="flex flex-col gap-2">
        <h4 className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
          Verified Resume Citation
        </h4>
        {claim.evidence ? (
          <div className="flex flex-col gap-3 rounded-xl border border-surface-container-high bg-surface-container p-4">
            <div className="flex items-center justify-between text-caption text-on-surface-variant">
              <span>Resume Page {claim.evidence.page}</span>
              {onViewOnDocument && (
                <button
                  type="button"
                  onClick={() => onViewOnDocument(claim)}
                  className="text-label-sm font-semibold text-primary hover:underline"
                >
                  Highlight on Document →
                </button>
              )}
            </div>
            <blockquote className="border-l-4 border-primary pl-3 font-serif text-body-md text-on-surface italic">
              &ldquo;{claim.evidence.quote}&rdquo;
            </blockquote>

          </div>
        ) : (
          <p className="text-body-sm italic text-on-surface-variant">
            No supporting citation found in the resume.
          </p>
        )}
      </div>

      {/* Overlapping Integrity Findings */}
      {hasFindings && (
        <div
          data-testid="claim-findings-section"
          className="flex flex-col gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-950"
        >
          <div className="flex items-center gap-2">
            <span aria-hidden="true">⚠</span>
            <h4 className="text-label-md font-semibold text-amber-950">
              Integrity Flags Overlapping Evidence ({claim.findings.length})
            </h4>
          </div>
          <p className="text-caption text-amber-900">
            Findings on cited text spans reduce the integrity factor of this claim from 1.0 to{" "}
            {claim.integrity_factor.toFixed(2)}.
          </p>
          <div className="flex flex-col gap-2">
            {claim.findings.map((f) => (
              <div
                key={f.finding_id}
                className="flex items-center justify-between rounded-lg border border-amber-200/60 bg-surface/80 px-3 py-2 text-body-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-mono text-caption font-semibold">{f.detector_id}</span>
                  <span>{f.detector_name || f.detector_id}</span>
                </div>
                <SeverityChip severity={f.severity} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scoring Factors Grid */}
      <div className="grid grid-cols-2 gap-3 rounded-xl bg-surface-container p-4 sm:grid-cols-3">
        <div>
          <span className="block text-[11px] uppercase tracking-wider text-on-surface-variant">
            Satisfaction
          </span>
          <span className="font-display text-title-md font-bold text-on-surface">
            {claim.satisfaction.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-wider text-on-surface-variant">
            Corroboration
          </span>
          <span className="font-display text-title-md font-bold text-on-surface">
            {claim.corroboration.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-wider text-on-surface-variant">
            Integrity Factor
          </span>
          <span
            className={`font-display text-title-md font-bold ${
              claim.integrity_factor < 1.0 ? "text-amber-700" : "text-on-surface"
            }`}
          >
            {claim.integrity_factor.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-wider text-on-surface-variant">
            Evidence Quality
          </span>
          <span className="font-display text-title-md font-bold text-on-surface">
            {claim.evidence_quality.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-wider text-on-surface-variant">
            Weight
          </span>
          <span className="font-display text-title-md font-bold text-on-surface">
            {claim.weight.toFixed(1)}
          </span>
        </div>
        <div>
          <span className="block text-[11px] uppercase tracking-wider text-primary">
            Contribution
          </span>
          <span className="font-display text-title-md font-bold text-primary">
            {claim.contribution.toFixed(2)} pts
          </span>
        </div>
      </div>
    </div>
  );
}
