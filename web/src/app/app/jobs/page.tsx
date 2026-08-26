"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { api } from "@/lib/api";
import type { JobSummary } from "@/lib/types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    setError(null);
    api.listJobs().then(setJobs).catch(setError);
  }, []);

  useEffect(load, [load]);

  return (
    <AsyncState loading={!jobs && !error} error={error} onRetry={load}>
      <div className="flex flex-col gap-6">
        {/* Page Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-headline-lg text-on-surface">Job Descriptions</h1>
            <p className="text-body-md text-on-surface-variant">
              Ingested job postings with discrete, testable extracted requirements
            </p>
          </div>
          <Link
            href="/app/jobs/new"
            className="rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary shadow-sm transition-opacity hover:opacity-90"
          >
            + Add Job Description
          </Link>
        </div>

        {/* Jobs List / Empty State */}
        {jobs && jobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-lowest p-12 text-center">
            <span className="text-4xl" aria-hidden="true">
              📄
            </span>
            <h3 className="mt-4 font-display text-title-lg text-on-surface">
              No Job Descriptions Added
            </h3>
            <p className="mt-1 max-w-md text-body-md text-on-surface-variant">
              Paste or upload a target job description to automatically extract requirements for resume matching.
            </p>
            <Link
              href="/app/jobs/new"
              className="mt-6 rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary"
            >
              Add Your First Job Description
            </Link>
          </div>
        ) : (
          <div className="flex flex-col divide-y divide-surface-container overflow-hidden rounded-2xl border border-outline-variant/30 bg-surface-container-lowest shadow-ocean">
            {jobs?.map((job) => (
              <div
                key={job.job_description_id}
                className="flex flex-col justify-between gap-4 p-6 transition-colors hover:bg-surface-container/30 sm:flex-row sm:items-center"
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-display text-title-md text-on-surface">
                      {job.title || "Job Posting"}
                    </h3>
                    <span
                      className={`rounded-md px-2 py-0.5 text-caption font-medium capitalize ${
                        job.state === "completed"
                          ? "bg-emerald-100 text-emerald-800"
                          : job.state === "failed"
                          ? "bg-rose-100 text-rose-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {job.state}
                    </span>
                  </div>
                  <p className="mt-1 text-body-sm text-on-surface-variant">
                    {job.company || "Unknown Company"}{" "}
                    {job.location ? `• ${job.location}` : ""} • Source: {job.source} •{" "}
                    {new Date(job.created_at).toLocaleDateString()}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    href={`/app/jobs/${job.job_description_id}`}
                    className="rounded-lg border border-outline-variant/40 bg-surface px-4 py-2 text-label-md font-semibold text-primary transition-colors hover:bg-surface-container"
                  >
                    View Requirements →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AsyncState>
  );
}
