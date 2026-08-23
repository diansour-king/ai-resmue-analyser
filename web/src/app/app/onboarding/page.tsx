"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, api } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.completeOnboarding(name);
      router.replace("/app/resume/upload");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "That did not save.");
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="font-display text-headline-lg-mobile text-on-surface md:text-headline-lg">
        What should we call you?
      </h1>
      <p className="mt-2 text-body-md text-on-surface-variant">
        This is the only thing we ask for. CareerLayer reads your resume; it does not need a
        profile.
      </p>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <label className="block">
          <span className="text-label-md text-on-surface-variant">Name</span>
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="mt-1 w-full rounded-lg border border-surface-container-highest bg-surface-container-lowest px-4 py-3 text-body-md outline-none focus:border-primary focus:ring-4 focus:ring-primary-fixed/50"
          />
        </label>
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-primary px-5 py-3 text-label-md text-on-primary disabled:opacity-60"
        >
          {saving ? "Saving…" : "Continue"}
        </button>
        {error ? (
          <p role="alert" className="text-body-md text-error">
            {error}
          </p>
        ) : null}
      </form>
    </div>
  );
}
