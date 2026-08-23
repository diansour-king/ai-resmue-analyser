"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { api } from "@/lib/api";
import type { ResumeSummary } from "@/lib/types";

const STATE_LABEL: Record<string, string> = {
  uploaded: "Received",
  queued: "Waiting to be analysed",
  processing: "Analysing",
  completed: "Analysed",
  failed: "Could not be analysed",
};

export default function ResumeListPage() {
  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    setError(null);
    api.listResumes().then(setResumes).catch(setError);
  }, []);

  useEffect(load, [load]);

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-display text-headline-lg-mobile text-on-surface md:text-headline-lg">
          Your resumes
        </h1>
        <Link
          href="/app/resume/upload"
          className="rounded-lg bg-primary px-5 py-3 text-label-md text-on-primary"
        >
          Upload a resume
        </Link>
      </div>

      <div className="mt-8">
        <AsyncState
          loading={resumes === null && !error}
          error={error}
          isEmpty={resumes?.length === 0}
          emptyTitle="No resumes yet"
          emptyBody="Upload a PDF and CareerLayer will show you what it found, where it found it, and why it matters."
          onRetry={load}
        >
          <ul className="space-y-3">
            {(resumes ?? []).map((resume) => (
              <li key={resume.resume_id}>
                <Link
                  href={`/app/resume/${resume.resume_id}`}
                  className="flex items-center justify-between rounded-lg border border-surface-container-high bg-surface-container-lowest p-5 shadow-ocean transition-colors hover:border-primary/40"
                >
                  <span>
                    <span className="block text-body-md font-semibold text-on-surface">
                      {resume.filename}
                    </span>
                    <span className="block text-caption text-on-surface-variant">
                      {resume.page_count ?? "?"} page(s) ·{" "}
                      {STATE_LABEL[resume.state] ?? resume.state}
                    </span>
                  </span>
                  <span aria-hidden className="text-primary">
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </AsyncState>
      </div>
    </div>
  );
}
