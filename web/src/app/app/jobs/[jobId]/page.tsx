"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { api } from "@/lib/api";
import type { JobDescription, JobRequirement } from "@/lib/types";

export default function JobDetailPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = use(params);
  const [job, setJob] = useState<JobDescription | null>(null);
  const [reqs, setReqs] = useState<JobRequirement[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    setError(null);
    Promise.all([api.getJob(jobId), api.getJobRequirements(jobId).catch(() => [])])
      .then(([j, r]) => {
        setJob(j);
        setReqs(r);
      })
      .catch(setError);
  }, [jobId]);

  useEffect(load, [load]);

  return (
    <AsyncState loading={!job && !error} error={error} onRetry={load}>
      {job && (
        <div className="flex flex-col gap-6">
          {/* Breadcrumb & Actions */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-body-md text-secondary">
              <Link href="/app/jobs" className="hover:text-primary">
                Job Descriptions
              </Link>
              <span aria-hidden="true">›</span>
              <span className="font-semibold text-on-surface">
                {job.title || "Job Detail"}
              </span>
            </div>

            <Link
              href={`/app/matches/new?job_id=${jobId}`}
              className="rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary shadow-sm hover:opacity-90"
            >
              Evaluate Against Resume →
            </Link>
          </div>

          {/* Job Overview Card */}
          <div className="flex flex-col gap-4 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean sm:p-8">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-label-sm font-semibold uppercase tracking-wider text-secondary">
                Job Overview
              </span>
              <span
                className={`rounded-md px-2.5 py-0.5 text-caption font-semibold capitalize ${
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

            <h1 className="font-display text-headline-lg text-on-surface">
              {job.title || "Untitled Job Description"}
            </h1>

            <div className="flex flex-wrap items-center gap-4 text-body-md text-on-surface-variant">
              {job.company && <span>Company: {job.company}</span>}
              {job.location && <span>Location: {job.location}</span>}
              <span>Source: {job.source}</span>
              <span>Created: {new Date(job.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Extracted Requirements Section */}
          <div className="flex flex-col gap-4 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean sm:p-8">
            <div className="border-b border-surface-container pb-4">
              <h2 className="font-display text-headline-md text-on-surface">
                Extracted Requirements ({reqs?.length ?? 0})
              </h2>
              <p className="text-caption text-on-surface-variant">
                Discrete criteria extracted by LLM with exact provenance citations from the posting.
              </p>
            </div>

            {reqs && reqs.length === 0 ? (
              <div className="p-8 text-center text-body-md text-on-surface-variant">
                {job.state === "completed"
                  ? "No structured requirements extracted from this job description."
                  : "Requirements extraction is still processing..."}
              </div>
            ) : (
              <div className="flex flex-col divide-y divide-surface-container">
                {reqs?.map((req) => (
                  <div key={req.requirement_id} className="flex flex-col gap-2 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-surface-container px-2 py-0.5 font-mono text-caption font-semibold">
                        #{req.ordinal}
                      </span>
                      <span
                        className={`rounded px-2 py-0.5 text-caption font-semibold uppercase ${
                          req.necessity === "required"
                            ? "bg-slate-200 text-slate-800"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {req.necessity}
                      </span>
                      <span className="rounded border border-outline-variant/30 px-2 py-0.5 text-caption text-on-surface-variant">
                        {req.kind.replace("_", " ")}
                      </span>
                      <span className="text-caption text-on-surface-variant">
                        Priority: {req.criticality}/3 (Weight: {req.weight.toFixed(1)})
                      </span>
                    </div>

                    <p className="text-body-md font-medium text-on-surface">{req.text}</p>

                    {req.evidence && (
                      <div className="rounded-lg bg-surface-container/50 px-3 py-2 text-caption text-on-surface-variant">
                        <span className="font-semibold text-secondary">Cited from posting:</span>{" "}
                        <span className="italic">&ldquo;{req.evidence.quote}&rdquo;</span>
                      </div>
                    )}

                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </AsyncState>
  );
}
