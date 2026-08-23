"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { api } from "@/lib/api";
import type { ResumeSummary } from "@/lib/types";

/**
 * Overview.
 *
 * The Stitch composition is kept: a page heading and a row of tiles. What the tiles say is
 * different. The six composite scores in the export - Resume Intelligence 82, Profile
 * Strength 87%, and the four sub-bars - had no definition and no source, and section 10 of
 * the specification rules out exactly that kind of number. Every figure here is a row count.
 */
export default function OverviewPage() {
  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    setError(null);
    api.listResumes().then(setResumes).catch(setError);
  }, []);

  useEffect(load, [load]);

  const analysed = (resumes ?? []).filter((r) => r.state === "completed").length;
  const working = (resumes ?? []).filter((r) =>
    ["uploaded", "queued", "processing"].includes(r.state),
  ).length;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-headline-lg-mobile text-on-surface md:text-headline-lg">
          Your resumes, read twice
        </h1>
        <p className="mt-2 text-body-md text-on-surface-variant">
          Here is what CareerLayer can actually show you about the documents you have uploaded.
        </p>
      </div>

      <AsyncState
        loading={resumes === null && !error}
        error={error}
        isEmpty={resumes?.length === 0}
        emptyTitle="Nothing analysed yet"
        emptyBody="Upload a resume and CareerLayer will show you what it found, where it found it, and why it matters."
        onRetry={load}
      >
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <Tile label="Resumes" value={resumes?.length ?? 0} />
          <Tile label="Analysed" value={analysed} />
          <Tile label="In progress" value={working} />
        </div>
      </AsyncState>

      <Link
        href="/app/resume/upload"
        className="inline-block rounded-lg bg-primary px-5 py-3 text-label-md text-on-primary"
      >
        Upload a resume
      </Link>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-surface-container-highest bg-surface-container-lowest p-5 shadow-ocean">
      <span className="text-label-md text-secondary">{label}</span>
      <span className="mt-2 block font-display text-display text-on-surface">{value}</span>
    </div>
  );
}
