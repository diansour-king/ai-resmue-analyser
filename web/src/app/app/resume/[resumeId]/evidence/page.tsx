"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { PageCanvas } from "@/components/PageCanvas";
import { SeverityChip } from "@/components/SeverityChip";
import { api } from "@/lib/api";
import { renderScale } from "@/lib/coordinates";
import type { Finding } from "@/lib/types";
import { useResume } from "@/lib/useResume";

/**
 * The evidence viewer.
 *
 * The Stitch two-pane composition is preserved exactly: the document on the left, the
 * intelligence panel on the right, each scrolling independently inside a rounded card. The
 * change is what the left pane holds. It was reflowed HTML text, which is the machine's read
 * of the document and therefore the half an adversary controls. It is now the rendered page
 * itself, with findings drawn on their real rectangles, which is the only way the product's
 * central claim can be shown rather than asserted.
 */
export default function EvidenceViewerPage({
  params,
}: {
  params: Promise<{ resumeId: string }>;
}) {
  const { resumeId } = use(params);
  const { resume, error, reload } = useResume(resumeId);
  const [findings, setFindings] = useState<Finding[] | null>(null);
  const [findingsError, setFindingsError] = useState<unknown>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const loadFindings = useCallback(() => {
    setFindingsError(null);
    api.getFindings(resumeId).then(setFindings).catch(setFindingsError);
  }, [resumeId]);

  useEffect(loadFindings, [loadFindings]);

  const page = resume?.pages.find((candidate) => candidate.page_number === pageNumber) ?? null;
  const onThisPage = useMemo(
    () => (findings ?? []).filter((finding) => finding.page === pageNumber),
    [findings, pageNumber],
  );
  const selected = (findings ?? []).find((f) => f.finding_id === selectedId) ?? null;
  const pageCount = resume?.pages.length ?? 0;

  /** Selecting a finding is what moves the page, so a finding is never selected off-screen. */
  const select = useCallback(
    (finding: Finding) => {
      setPageNumber(finding.page);
      setSelectedId(finding.finding_id);
    },
    [],
  );

  const byPage = useMemo(() => {
    const groups = new Map<number, Finding[]>();
    for (const finding of findings ?? []) {
      groups.set(finding.page, [...(groups.get(finding.page) ?? []), finding]);
    }
    return [...groups.entries()].sort(([a], [b]) => a - b);
  }, [findings]);

  return (
    <AsyncState loading={!resume && !error} error={error} onRetry={reload}>
      {resume ? (
        <div className="flex h-full flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2 text-body-md text-secondary">
            <Link href={`/app/resume/${resumeId}`} className="hover:text-primary">
              Resume Analysis
            </Link>
            <span aria-hidden>›</span>
            <span className="font-semibold text-on-surface">Evidence Grounding</span>
          </div>

          <div className="flex flex-col gap-gutter lg:flex-row">
            <section className="flex flex-[2] flex-col overflow-hidden rounded-xl border border-surface-container-high bg-surface-container-lowest shadow-ocean">
              <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-3 border-b border-surface-container bg-surface-container-lowest/90 px-6 py-4 backdrop-blur-md">
                <div>
                  <h2 className="font-display text-headline-md text-on-surface">
                    What a human sees
                  </h2>
                  <p className="text-caption text-on-surface-variant">
                    The original page, rendered at {page?.render_dpi ?? 200} DPI
                    {page && renderScale(page)
                      ? ` (${renderScale(page)?.toFixed(2)} pixels per point)`
                      : ""}
                    .
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
                  <span className="text-label-md text-on-surface-variant">
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
              <div className="max-h-[70vh] overflow-y-auto p-6">
                {page ? (
                  <PageCanvas
                    resumeId={resumeId}
                    page={page}
                    findings={onThisPage}
                    selectedFindingId={selectedId}
                    onSelect={setSelectedId}
                  />
                ) : (
                  <p className="text-body-md text-on-surface-variant">No such page.</p>
                )}
              </div>
            </section>

            <aside className="flex w-full shrink-0 flex-col overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-bright shadow-ocean lg:w-[420px]">
              <div className="border-b border-outline-variant/20 bg-surface-container-lowest px-6 py-5">
                <h2 className="font-display text-[20px] leading-tight text-primary">
                  What the machine reads
                </h2>
                <p className="mt-1 text-caption text-on-surface-variant">
                  The PDF text layer, and where it disagrees with the page above.
                </p>
              </div>

              <div className="flex-1 space-y-6 overflow-y-auto p-6">
                <AsyncState
                  loading={findings === null && !findingsError}
                  error={findingsError}
                  isEmpty={findings?.length === 0}
                  emptyTitle="Nothing flagged"
                  emptyBody="The text layer and the rendered pages agree on this document."
                  onRetry={loadFindings}
                >
                  {selected ? <FindingDetail finding={selected} /> : null}

                  {byPage.map(([number, group]) => (
                    <div key={number}>
                      <p className="mb-2 text-label-md uppercase tracking-wider text-secondary">
                        Page {number}
                      </p>
                      <ul className="space-y-2">
                        {group.map((finding) => (
                          <li key={finding.finding_id}>
                            <button
                              type="button"
                              onClick={() => select(finding)}
                              aria-pressed={finding.finding_id === selectedId}
                              data-testid={`finding-${finding.finding_id}`}
                              className={`w-full rounded-lg border p-4 text-left transition-colors ${
                                finding.finding_id === selectedId
                                  ? "border-primary bg-primary-fixed/30"
                                  : "border-surface-container-highest bg-surface-container-lowest hover:border-primary/40"
                              }`}
                            >
                              <span className="flex items-center justify-between gap-2">
                                <span className="font-mono text-caption text-secondary">
                                  {finding.detector_id} · {finding.detector_name}
                                </span>
                                <SeverityChip severity={finding.severity} />
                              </span>
                              <span className="mt-2 block truncate text-body-md text-on-surface">
                                {finding.excerpt}
                              </span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </AsyncState>
              </div>
            </aside>
          </div>
        </div>
      ) : null}
    </AsyncState>
  );
}

function FindingDetail({ finding }: { finding: Finding }) {
  return (
    <div
      data-testid="finding-detail"
      className="rounded-xl border border-primary/30 bg-surface-container-lowest p-5 shadow-ocean"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-display text-headline-md text-on-surface">
          {finding.detector_name}
        </h3>
        <SeverityChip severity={finding.severity} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-caption">
        <dt className="text-on-surface-variant">Detector</dt>
        <dd className="font-mono text-on-surface">{finding.detector_id}</dd>
        <dt className="text-on-surface-variant">Confidence</dt>
        <dd className="text-on-surface">{Math.round(finding.confidence * 100)}%</dd>
        <dt className="text-on-surface-variant">Page</dt>
        <dd className="text-on-surface">{finding.page}</dd>
        <dt className="text-on-surface-variant">Location (PDF points)</dt>
        <dd className="font-mono text-on-surface">
          {finding.bbox.x0.toFixed(0)}, {finding.bbox.y0.toFixed(0)} →{" "}
          {finding.bbox.x1.toFixed(0)}, {finding.bbox.y1.toFixed(0)}
        </dd>
      </dl>
      <div className="mt-4">
        <p className="text-label-md uppercase tracking-wider text-secondary">Extracted text</p>
        <p className="mt-1 border-l-4 border-primary bg-surface p-3 text-body-md italic text-on-surface-variant">
          {finding.excerpt}
        </p>
      </div>
      <div className="mt-4">
        <p className="text-label-md uppercase tracking-wider text-secondary">Why it matters</p>
        <p className="mt-1 text-body-md text-on-surface-variant">{finding.rationale}</p>
      </div>
    </div>
  );
}
