"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { toDisplayRect } from "@/lib/coordinates";
import type { Finding, PageInfo } from "@/lib/types";

const OUTLINE: Record<string, string> = {
  high: "border-error bg-error/15",
  suspicious: "border-[#b5760c] bg-[#ffb703]/15",
  info: "border-primary bg-primary/10",
};

/**
 * The left half of the evidence viewer: the page as a human sees it, with what the machine
 * found drawn on top of it.
 *
 * The overlay measures the image as displayed and scales the PDF-point rectangles to match,
 * recomputing on every resize. No factor is hardcoded here, and none is stored in the
 * database - the transform lives in one function and is unit tested.
 */
export function PageCanvas({
  resumeId,
  page,
  findings,
  selectedFindingId,
  onSelect,
}: {
  resumeId: string;
  page: PageInfo;
  findings: Finding[];
  selectedFindingId: string | null;
  onSelect: (findingId: string) => void;
}) {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [displayed, setDisplayed] = useState({ width: 0, height: 0 });
  const [failed, setFailed] = useState(false);

  const measure = useCallback(() => {
    const image = imageRef.current;
    if (image) setDisplayed({ width: image.clientWidth, height: image.clientHeight });
  }, []);

  useEffect(() => {
    const image = imageRef.current;
    if (!image || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(image);
    return () => observer.disconnect();
  }, [measure]);

  useEffect(() => {
    setFailed(false);
  }, [page.page_number, resumeId]);

  if (!page.render_available) {
    return (
      <div className="flex h-full items-center justify-center p-10 text-center">
        <p className="text-body-md text-on-surface-variant">
          This page has not been rendered yet.
        </p>
      </div>
    );
  }

  if (failed) {
    return (
      <div role="alert" className="flex h-full items-center justify-center p-10 text-center">
        <p className="text-body-md text-on-surface-variant">
          The rendered page could not be loaded.
        </p>
      </div>
    );
  }

  return (
    <div className="relative mx-auto w-full max-w-3xl">
      {/* eslint-disable-next-line @next/next/no-img-element -- the render is streamed
          through the API with a session cookie; next/image would proxy it through the
          optimiser and lose the credential. */}
      <img
        ref={imageRef}
        src={api.pageRenderUrl(resumeId, page.page_number)}
        alt={`Page ${page.page_number} of the resume, as printed`}
        className="w-full rounded-lg border border-surface-container-high shadow-ocean"
        onLoad={measure}
        onError={() => setFailed(true)}
      />
      <div className="pointer-events-none absolute inset-0">
        {findings.map((finding) => {
          const rect = toDisplayRect(finding.bbox, page, displayed);
          const selected = finding.finding_id === selectedFindingId;
          return (
            <button
              key={finding.finding_id}
              type="button"
              aria-label={`${finding.detector_name}, ${finding.severity}`}
              data-testid={`overlay-${finding.finding_id}`}
              onClick={() => onSelect(finding.finding_id)}
              className={`pointer-events-auto absolute rounded-sm border-2 transition-shadow ${
                OUTLINE[finding.severity] ?? OUTLINE.info
              } ${selected ? "ring-2 ring-primary ring-offset-2" : ""}`}
              style={{
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height,
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
