"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, use, useCallback, useEffect, useMemo, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { ClaimDetail } from "@/components/ClaimDetail";
import { PageCanvas } from "@/components/PageCanvas";
import { api } from "@/lib/api";
import { renderScale } from "@/lib/coordinates";
import type { Finding, MatchClaim, MatchRun } from "@/lib/types";
import { useResume } from "@/lib/useResume";



function MatchEvidenceContent({ matchId }: { matchId: string }) {
  const searchParams = useSearchParams();
  const initialClaimId = searchParams.get("claim_id");

  const [match, setMatch] = useState<MatchRun | null>(null);
  const [matchError, setMatchError] = useState<unknown>(null);
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(initialClaimId);
  const [pageNumber, setPageNumber] = useState(1);
  const [findings, setFindings] = useState<Finding[] | null>(null);

  const loadMatch = useCallback(() => {
    setMatchError(null);
    api
      .getMatch(matchId)
      .then((data) => {
        setMatch(data);
        if (!selectedClaimId && data.claims.length > 0) {
          setSelectedClaimId(data.claims[0].claim_id);
          if (data.claims[0].evidence) {
            setPageNumber(data.claims[0].evidence.page);
          }
        } else if (selectedClaimId) {
          const found = data.claims.find((c) => c.claim_id === selectedClaimId);
          if (found && found.evidence) {
            setPageNumber(found.evidence.page);
          }
        }
      })
      .catch(setMatchError);
  }, [matchId, selectedClaimId]);

  useEffect(loadMatch, [loadMatch]);

  // Load underlying resume and findings
  const resumeId = match?.resume_id || "";
  const { resume, error: resumeError, reload: reloadResume } = useResume(resumeId);

  useEffect(() => {
    if (resumeId) {
      api.getFindings(resumeId).then(setFindings).catch(() => setFindings([]));
    }
  }, [resumeId]);

  const selectedClaim = useMemo(
    () => match?.claims.find((c) => c.claim_id === selectedClaimId) ?? null,
    [match, selectedClaimId],
  );

  const handleSelectClaim = (claim: MatchClaim) => {
    setSelectedClaimId(claim.claim_id);
    if (claim.evidence) {
      setPageNumber(claim.evidence.page);
    }
  };

  const page = resume?.pages.find((p) => p.page_number === pageNumber) ?? null;
  const pageCount = resume?.pages.length ?? 1;

  // Synthesize evidence box as a finding-like highlight for PageCanvas if present
  const canvasOverlays: Finding[] = useMemo(() => {
    const overlays: Finding[] = [];

    // Add overlapping integrity findings for this page
    for (const f of findings ?? []) {
      if (f.page === pageNumber) {
        overlays.push(f);
      }
    }

    // If selected claim has evidence on this page with a bbox, add as primary highlight
    if (
      selectedClaim &&
      selectedClaim.evidence &&
      selectedClaim.evidence.page === pageNumber &&
      selectedClaim.evidence.bbox
    ) {
      const [x0, y0, x1, y1] = selectedClaim.evidence.bbox;
      overlays.push({
        finding_id: `evidence-${selectedClaim.claim_id}`,
        detector_id: "EVIDENCE",
        detector_name: "Cited Match Evidence",
        severity: "info",
        confidence: selectedClaim.confidence,
        page: selectedClaim.evidence.page,
        bbox: { x0, y0, x1, y1 },
        excerpt: selectedClaim.evidence.quote,
        rationale: selectedClaim.rationale || "Supporting evidence for requirement.",
      });
    }

    return overlays;
  }, [findings, pageNumber, selectedClaim]);

  return (
    <AsyncState
      loading={!match && !matchError}
      error={matchError || resumeError}
      onRetry={() => {
        loadMatch();
        reloadResume();
      }}
    >
      {match && (
        <div className="flex h-full flex-col gap-4">
          {/* Breadcrumbs */}
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
              <span className="font-semibold text-on-surface">Grounded Evidence Viewer</span>
            </div>

            <Link
              href={`/app/matches/${matchId}`}
              className="rounded-lg border border-outline-variant/40 px-3 py-1.5 text-label-sm font-medium text-on-surface-variant hover:bg-surface-container"
            >
              ← Back to Match Overview
            </Link>
          </div>

          {/* Two-Pane Evidence Layout */}
          <div className="flex flex-col gap-gutter lg:flex-row">
            {/* Left Pane: Rendered Document with Highlight Overlay */}
            <section className="flex flex-[3] flex-col overflow-hidden rounded-xl border border-surface-container-high bg-surface-container-lowest shadow-ocean">
              {/* Document Header & Page Navigation */}
              <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-surface-container bg-surface-container-lowest/90 px-6 py-4 backdrop-blur-md">
                <div>
                  <h2 className="font-display text-headline-md text-on-surface">
                    Verified Document Page
                  </h2>
                  <p className="text-caption text-on-surface-variant">
                    Rendered at {page?.render_dpi ?? 200} DPI
                    {page && renderScale(page)
                      ? ` (${renderScale(page)?.toFixed(2)} px/pt)`
                      : ""}
                    . Showing cited citations and integrity findings.
                  </p>
                </div>

                <nav className="flex items-center gap-2" aria-label="Page navigation">
                  <button
                    type="button"
                    onClick={() => setPageNumber((n) => Math.max(1, n - 1))}
                    disabled={pageNumber <= 1}
                    className="rounded-lg bg-surface-container px-3 py-2 text-label-md text-on-surface disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <span className="px-2 text-body-sm font-semibold text-on-surface">
                    Page {pageNumber} of {pageCount}
                  </span>
                  <button
                    type="button"
                    onClick={() => setPageNumber((n) => Math.min(pageCount, n + 1))}
                    disabled={pageNumber >= pageCount}
                    className="rounded-lg bg-surface-container px-3 py-2 text-label-md text-on-surface disabled:opacity-40"
                  >
                    Next
                  </button>
                </nav>
              </div>

              {/* Page Canvas with Highlight Overlay */}
              <div className="overflow-auto p-4 sm:p-6">
                {page && resumeId ? (
                  <PageCanvas
                    resumeId={resumeId}
                    page={page}
                    findings={canvasOverlays}
                    selectedFindingId={
                      selectedClaim
                        ? `evidence-${selectedClaim.claim_id}`
                        : null
                    }
                    onSelect={() => {}}
                  />
                ) : (
                  <div className="p-12 text-center text-body-md text-on-surface-variant">
                    Document rendering unavailable.
                  </div>
                )}
              </div>
            </section>

            {/* Right Pane: Requirements Claims List & Detail Inspector */}
            <section className="flex flex-[2] flex-col gap-4">
              {/* Claims Selector Carousel / List */}
              <div className="flex flex-col gap-2 rounded-xl border border-surface-container-high bg-surface-container-lowest p-4 shadow-ocean">
                <h3 className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
                  Select Requirement to Highlight ({match.claims.length})
                </h3>
                <div className="max-h-56 overflow-y-auto divide-y divide-surface-container">
                  {match.claims.map((c) => {
                    const isSelected = c.claim_id === selectedClaimId;
                    return (
                      <button
                        key={c.claim_id}
                        type="button"
                        onClick={() => handleSelectClaim(c)}
                        className={`flex w-full items-center justify-between gap-2 p-2.5 text-left transition-colors ${
                          isSelected
                            ? "bg-secondary-container font-semibold text-on-secondary-container"
                            : "hover:bg-surface-container/50 text-on-surface"
                        }`}
                      >
                        <span className="truncate text-body-sm">{c.requirement_text}</span>
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            c.met
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-rose-100 text-rose-800"
                          }`}
                        >
                          {c.met ? "Met" : "Unmet"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Inspector for currently highlighted claim */}
              <ClaimDetail claim={selectedClaim} />
            </section>
          </div>
        </div>
      )}
    </AsyncState>
  );
}

export default function MatchEvidencePage({
  params,
}: {
  params: Promise<{ matchId: string }>;
}) {
  const { matchId } = use(params);

  return (
    <Suspense fallback={<div className="p-8 text-body-md">Loading Evidence Viewer...</div>}>
      <MatchEvidenceContent matchId={matchId} />
    </Suspense>
  );
}
