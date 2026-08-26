"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { api } from "@/lib/api";
import type { JobSummary, ResumeSummary } from "@/lib/types";

function NewMatchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialJobId = searchParams.get("job_id") || "";
  const initialResumeId = searchParams.get("resume_id") || "";

  const [resumes, setResumes] = useState<ResumeSummary[] | null>(null);
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState(initialResumeId);
  const [selectedJobId, setSelectedJobId] = useState(initialJobId);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState<unknown>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const loadData = useCallback(() => {
    setPageError(null);
    Promise.all([api.listResumes(), api.listJobs()])
      .then(([resList, jobList]) => {
        setResumes(resList);
        setJobs(jobList);
        if (!selectedResumeId && resList.length > 0) {
          setSelectedResumeId(resList[0].resume_id);
        }
        if (!selectedJobId && jobList.length > 0) {
          setSelectedJobId(jobList[0].job_description_id);
        }
      })
      .catch(setPageError);
  }, [selectedResumeId, selectedJobId]);

  useEffect(loadData, [loadData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedResumeId || !selectedJobId) {
      setSubmitError("Please select both a resume and a job description.");
      return;
    }

    setSubmitError(null);
    setLoading(true);

    try {
      const res = await api.createMatch(selectedResumeId, selectedJobId);
      router.push(`/app/matches/${res.match_run_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initiate match run.";
      setSubmitError(msg);
      setLoading(false);
    }
  };

  return (
    <AsyncState loading={(!resumes || !jobs) && !pageError} error={pageError} onRetry={loadData}>
      <div className="mx-auto flex max-w-2xl flex-col gap-6">
        <div>
          <h1 className="font-display text-headline-lg text-on-surface">New Match Evaluation</h1>
          <p className="text-body-md text-on-surface-variant">
            Select a verified resume and a target job description to run deterministic requirement
            matching and integrity analysis.
          </p>
        </div>

        {resumes && resumes.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-lowest p-8 text-center">
            <p className="text-body-md text-on-surface-variant">
              You haven&apos;t uploaded any resumes yet.
            </p>
            <Link
              href="/app/resume/upload"
              className="mt-4 inline-block rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary"
            >
              Upload Resume
            </Link>
          </div>
        ) : jobs && jobs.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-outline-variant/40 bg-surface-container-lowest p-8 text-center">
            <p className="text-body-md text-on-surface-variant">
              You haven&apos;t added any job descriptions yet.
            </p>

            <Link
              href="/app/jobs/new"
              className="mt-4 inline-block rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary"
            >
              Add Job Description
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-6 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean sm:p-8"
          >
            {/* Resume selector */}
            <div className="flex flex-col gap-2">
              <label htmlFor="select-resume" className="text-label-md font-semibold text-on-surface">
                1. Select Resume
              </label>
              <select
                id="select-resume"
                value={selectedResumeId}
                onChange={(e) => setSelectedResumeId(e.target.value)}
                className="rounded-xl border border-outline-variant/40 bg-surface p-3.5 text-body-md text-on-surface focus:border-primary focus:outline-none"
              >
                {resumes?.map((r) => (
                  <option key={r.resume_id} value={r.resume_id}>
                    {r.filename} ({r.state})
                  </option>
                ))}
              </select>
            </div>

            {/* Job Description selector */}
            <div className="flex flex-col gap-2">
              <label htmlFor="select-job" className="text-label-md font-semibold text-on-surface">
                2. Select Target Job Description
              </label>
              <select
                id="select-job"
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="rounded-xl border border-outline-variant/40 bg-surface p-3.5 text-body-md text-on-surface focus:border-primary focus:outline-none"
              >
                {jobs?.map((j) => (
                  <option key={j.job_description_id} value={j.job_description_id}>
                    {j.title || "Job Posting"} {j.company ? `(${j.company})` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Error banner */}
            {submitError && (
              <div
                role="alert"
                className="rounded-xl border border-error/30 bg-error/10 p-4 text-body-sm text-error"
              >
                {submitError}
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => router.back()}
                className="rounded-xl border border-outline-variant/40 px-5 py-2.5 text-label-md font-semibold text-on-surface-variant hover:bg-surface-container"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="rounded-xl bg-primary px-6 py-2.5 text-label-md font-semibold text-on-primary shadow-sm hover:opacity-90 disabled:opacity-50"
              >
                {loading ? "Starting Evaluation..." : "Start Match Run"}
              </button>
            </div>
          </form>
        )}
      </div>
    </AsyncState>
  );
}

export default function NewMatchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-body-md">Loading...</div>}>
      <NewMatchContent />
    </Suspense>
  );
}
