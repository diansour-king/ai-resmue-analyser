"use client";

import type { CandidateSkillGap, GapCategory, GapItem } from "@/lib/types";

export function getCategoryBadge(category: GapCategory) {
  switch (category) {
    case "missing":
      return {
        label: "Missing Evidence",
        classes: "bg-rose-100 text-rose-800 border-rose-200",
        icon: "✕",
      };
    case "partial":
      return {
        label: "Partial Match",
        classes: "bg-sky-100 text-sky-800 border-sky-200",
        icon: "≈",
      };
    case "unverifiable":
      return {
        label: "Unverifiable",
        classes: "bg-amber-100 text-amber-900 border-amber-300",
        icon: "⚠",
      };
  }
}

export function GapList({
  candidates,
  gaps,
  selectedSkills,
  onToggleSkill,
}: {
  candidates: CandidateSkillGap[];
  gaps: GapItem[];
  selectedSkills: Set<string>;
  onToggleSkill: (skill: string) => void;
}) {
  if (candidates.length === 0 && gaps.length === 0) {
    return (
      <div
        data-testid="empty-gaps"
        className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-lowest p-8 text-center"
      >
        <span className="text-3xl" aria-hidden="true">
          ✨
        </span>
        <h4 className="mt-2 font-display text-title-md text-on-surface">No Skill Gaps Identified</h4>
        <p className="mt-1 text-caption text-on-surface-variant">
          Your resume satisfies all evaluated requirements with verified, clean evidence.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean">
      <div className="border-b border-surface-container pb-4">
        <h3 className="font-display text-headline-md text-on-surface">Skill Gap Simulator</h3>
        <p className="text-caption text-on-surface-variant">
          Toggle candidate skills to simulate server-projected score uplifts. Projections are
          calculated using deterministic scoring models without client-side addition.
        </p>
      </div>

      {/* Candidate Interactive Toggles */}
      <div className="flex flex-col gap-3">
        <h4 className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
          Target Candidate Skills ({candidates.length})
        </h4>

        <div className="flex flex-col divide-y divide-surface-container">
          {candidates.map((candidate) => {
            const isChecked = selectedSkills.has(candidate.skill);
            const badge = getCategoryBadge(candidate.category);
            const linkedGaps = gaps.filter((g) => candidate.requirement_ids.includes(g.requirement_id));

            return (
              <div
                key={candidate.skill}
                data-testid={`candidate-row-${candidate.skill}`}
                onClick={() => onToggleSkill(candidate.skill)}
                className={`group flex cursor-pointer flex-col gap-3 rounded-xl p-4 transition-colors ${
                  isChecked
                    ? "bg-secondary-container/40 border-l-4 border-l-primary"
                    : "hover:bg-surface-container/40"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}} // handled by parent onClick
                      className="h-5 w-5 rounded border-outline-variant text-primary focus:ring-primary"
                      aria-label={`Toggle ${candidate.skill}`}
                    />
                    <div>
                      <span className="font-display text-title-md font-semibold text-on-surface">
                        {candidate.skill}
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-caption font-semibold ${badge.classes}`}
                    >
                      <span aria-hidden="true">{badge.icon}</span>
                      {badge.label}
                    </span>

                    <span className="rounded-md bg-surface-container px-2 py-0.5 text-caption font-mono font-medium text-primary">
                      +{candidate.points_available.toFixed(1)} pts available
                    </span>
                  </div>
                </div>

                {/* Linked Requirements Preview */}
                {linkedGaps.length > 0 && (
                  <div className="ml-8 flex flex-col gap-1 text-caption text-on-surface-variant">
                    {linkedGaps.map((lg) => (
                      <div key={lg.requirement_id} className="flex items-baseline gap-1.5">
                        <span className="text-secondary">•</span>
                        <span>{lg.requirement_text}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Complete Requirements Gaps List */}
      <div className="mt-4 flex flex-col gap-3 border-t border-surface-container pt-4">
        <h4 className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
          All Requirement Gaps ({gaps.length})
        </h4>

        <div className="flex flex-col divide-y divide-surface-container">
          {gaps.map((gap) => {
            const badge = getCategoryBadge(gap.category);
            return (
              <div key={gap.requirement_id} className="flex flex-col gap-2 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-body-md text-on-surface">
                    {gap.requirement_text}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 text-[11px] font-semibold uppercase ${badge.classes}`}
                    >
                      {badge.label}
                    </span>
                    <span className="text-caption font-semibold text-secondary">
                      {gap.points_available.toFixed(1)} pts
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-[11px] text-on-surface-variant">
                  <span>Necessity: {gap.necessity}</span>
                  <span>Criticality: {gap.criticality}/3</span>
                  <span>Weight: {gap.weight.toFixed(1)}</span>
                  <span>Current satisfaction: {gap.current_satisfaction.toFixed(2)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
