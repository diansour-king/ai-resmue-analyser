"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";

export default function NewJobPage() {
  const router = useRouter();
  const [tab, setTab] = useState<"paste" | "upload">("paste");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [rawText, setRawText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (tab === "paste") {
        if (!rawText.trim()) {
          setError("Please paste the job description text.");
          setLoading(false);
          return;
        }
        const res = await api.createJob({
          raw_text: rawText.trim(),
          title: title.trim() || null,
          company: company.trim() || null,
          location: location.trim() || null,
        });
        router.push(`/app/jobs/${res.job_description_id}`);
      } else {
        if (!file) {
          setError("Please select a PDF file.");
          setLoading(false);
          return;
        }
        const res = await api.uploadJob(file, {
          title: title.trim() || undefined,
          company: company.trim() || undefined,
          location: location.trim() || undefined,
        });
        router.push(`/app/jobs/${res.job_description_id}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to ingest job description.";
      setError(msg);
      setLoading(false);
    }

  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-headline-lg text-on-surface">Add Job Description</h1>
        <p className="text-body-md text-on-surface-variant">
          Paste the job posting text or upload a PDF document. Requirements will be extracted
          into structured, testable criteria.
        </p>
      </div>

      {/* Form Card */}
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-6 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-6 shadow-ocean sm:p-8"
      >
        {/* Tab selection: Paste vs Upload */}
        <div className="flex border-b border-surface-container pb-4">
          <div className="flex rounded-xl border border-outline-variant/30 bg-surface p-1 text-label-md">
            <button
              type="button"
              onClick={() => setTab("paste")}
              className={`rounded-lg px-4 py-2 transition-colors ${
                tab === "paste"
                  ? "bg-primary text-on-primary font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Paste Text
            </button>
            <button
              type="button"
              onClick={() => setTab("upload")}
              className={`rounded-lg px-4 py-2 transition-colors ${
                tab === "upload"
                  ? "bg-primary text-on-primary font-semibold"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Upload PDF
            </button>
          </div>
        </div>

        {/* Metadata Inputs */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="job-title" className="text-label-sm font-semibold text-on-surface">
              Job Title
            </label>
            <input
              id="job-title"
              type="text"
              placeholder="e.g. Senior Backend Engineer"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="rounded-xl border border-outline-variant/40 bg-surface px-3.5 py-2 text-body-md text-on-surface focus:border-primary focus:outline-none"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="job-company" className="text-label-sm font-semibold text-on-surface">
              Company Name
            </label>
            <input
              id="job-company"
              type="text"
              placeholder="e.g. TechFlow Systems"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="rounded-xl border border-outline-variant/40 bg-surface px-3.5 py-2 text-body-md text-on-surface focus:border-primary focus:outline-none"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="job-location" className="text-label-sm font-semibold text-on-surface">
              Location
            </label>
            <input
              id="job-location"
              type="text"
              placeholder="e.g. Remote / New York"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="rounded-xl border border-outline-variant/40 bg-surface px-3.5 py-2 text-body-md text-on-surface focus:border-primary focus:outline-none"
            />
          </div>
        </div>

        {/* Body input based on Tab */}
        {tab === "paste" ? (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="job-text" className="text-label-sm font-semibold text-on-surface">
              Job Description Text *
            </label>
            <textarea
              id="job-text"
              rows={12}
              required
              placeholder="Paste full job description including responsibilities and requirements..."
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              className="rounded-xl border border-outline-variant/40 bg-surface p-4 font-mono text-body-sm text-on-surface focus:border-primary focus:outline-none"
            />
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <label className="text-label-sm font-semibold text-on-surface">
              Select Job Description PDF *
            </label>
            <input
              type="file"
              accept="application/pdf"
              required
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="rounded-xl border border-outline-variant/40 bg-surface p-4 text-body-md text-on-surface file:mr-4 file:rounded-lg file:border-0 file:bg-secondary-container file:px-4 file:py-2 file:text-label-md file:font-semibold file:text-on-secondary-container"
            />
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div role="alert" className="rounded-xl border border-error/30 bg-error/10 p-4 text-body-sm text-error">
            {error}
          </div>
        )}

        {/* Submit button */}
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
            {loading ? "Processing Job..." : "Extract Requirements"}
          </button>
        </div>
      </form>
    </div>
  );
}
