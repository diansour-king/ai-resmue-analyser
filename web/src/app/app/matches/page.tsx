"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { MatchList } from "@/components/MatchList";
import { api } from "@/lib/api";
import type { MatchSummary } from "@/lib/types";

export default function MatchesPage() {
  const [matches, setMatches] = useState<MatchSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(() => {
    setError(null);
    api
      .listMatches()
      .then((res) => setMatches(res.items))
      .catch(setError);
  }, []);

  useEffect(load, [load]);

  return (
    <AsyncState loading={!matches && !error} error={error} onRetry={load}>
      <div className="flex flex-col gap-6">
        {/* Page Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="font-display text-headline-lg text-on-surface">Match Evaluations</h1>
            <p className="text-body-md text-on-surface-variant">
              Deterministic, evidence-grounded evaluations of resumes against target job descriptions
            </p>
          </div>
          <Link
            href="/app/matches/new"
            className="rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary shadow-sm hover:opacity-90"
          >
            + Evaluate New Match
          </Link>
        </div>

        {/* Matches List */}
        {matches && <MatchList matches={matches} />}
      </div>
    </AsyncState>
  );
}
