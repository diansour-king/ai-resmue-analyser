"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useCallback, useEffect, useState } from "react";

import { AsyncState } from "@/components/AsyncState";
import { ClaimDetail } from "@/components/ClaimDetail";
import { RequirementTable } from "@/components/RequirementTable";
import { ScoreCard } from "@/components/ScoreCard";
import { api } from "@/lib/api";
import type { MatchClaim, MatchRun } from "@/lib/types";

export default function MatchResultPage({
  params,
}: {
  params: Promise<{ matchId: string }>;
}) {
  const { matchId } = use(params);
  const router = useRouter();

  const [match, setMatch] = useState<MatchRun | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [selectedClaim, setSelectedClaim] = useState<MatchClaim | null>(null);
  const [liveStage, setLiveStage] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    api
      .getMatch(matchId)
      .then((data) => {
        setMatch(data);
        if (data.claims && data.claims.length > 0 && !selectedClaim) {
          setSelectedClaim(data.claims[0]);
        }
      })
      .catch(setError);
  }, [matchId, selectedClaim]);

  useEffect(load, [load]);

  const matchState = match?.state;

  // Server-Sent Events (SSE) stream for live match updates if queued or processing
  useEffect(() => {
    if (!matchState || matchState === "completed" || matchState === "failed") {
      return;
    }

    setLiveStage(matchState);
    let eventSource: EventSource | null = null;

    try {
      eventSource = new EventSource(api.matchEventsUrl(matchId), {
        withCredentials: true,
      });

      eventSource.addEventListener("queued", () => {
        setLiveStage("queued");
      });

      eventSource.addEventListener("scoring", () => {
        setLiveStage("scoring");
      });

      eventSource.addEventListener("canary", () => {
        setLiveStage("canary");
      });

      eventSource.addEventListener("complete", () => {
        setLiveStage("complete");
        eventSource?.close();
        load();
      });

      eventSource.addEventListener("failed", () => {
        setLiveStage("failed");
        eventSource?.close();
        load();
      });

      eventSource.onerror = () => {
        // If SSE fails or disconnects, fallback to periodic polling until terminal state
        eventSource?.close();
        const interval = setInterval(() => {
          api
            .getMatch(matchId)
            .then((updated) => {
              if (updated.state === "completed" || updated.state === "failed") {
                clearInterval(interval);
                setMatch(updated);
              }
            })
            .catch(() => {});
        }, 2000);

        return () => clearInterval(interval);
      };
    } catch {
      // Fallback
    }

    return () => {
      eventSource?.close();
    };
  }, [matchId, matchState, load]);


  const handleViewOnDocument = (claim: MatchClaim) => {
    router.push(`/app/matches/${matchId}/evidence?claim_id=${claim.claim_id}`);
  };

  const isProcessing =
    match && (match.state === "queued" || match.state === "processing");

  return (
    <AsyncState loading={!match && !error} error={error} onRetry={load}>
      {match && (
        <div className="flex flex-col gap-6">
          {/* Breadcrumb Navigation */}
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-body-md text-secondary">
              <Link href="/app/matches" className="hover:text-primary">
                Match Evaluations
              </Link>
              <span aria-hidden="true">›</span>
              <span className="font-semibold text-on-surface">
                {match.job.title || "Match Result"}
              </span>
            </div>

            {match.state === "completed" && (
              <Link
                href={`/app/matches/${matchId}/evidence`}
                className="rounded-xl border border-primary bg-secondary-container px-4 py-2 text-label-md font-semibold text-on-secondary-container transition-colors hover:bg-secondary-container/80"
              >
                Open Grounded Evidence Viewer ↗
              </Link>
            )}
          </div>

          {/* Live Processing Indicator */}
          {isProcessing && (
            <div
              role="status"
              aria-live="polite"
              data-testid="match-processing-state"
              className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-12 text-center shadow-ocean"
            >
              <div
                className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent"
                aria-hidden="true"
              />
              <div>
                <h3 className="font-display text-headline-sm text-on-surface">
                  Evaluating Resume Against Job Requirements...
                </h3>
                <p className="mt-1 text-body-md text-on-surface-variant">
                  Stage:{" "}
                  <span className="font-semibold text-primary capitalize">
                    {liveStage || match.state}
                  </span>{" "}
                  • Extracting citations and executing deterministic scoring model.
                </p>
              </div>
            </div>
          )}

          {/* Failed Match State */}
          {match.state === "failed" && (
            <div
              role="alert"
              data-testid="match-failed-state"
              className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-error/30 bg-error/5 p-10 text-center"
            >
              <span className="text-4xl text-error" aria-hidden="true">
                ✕
              </span>
              <div>
                <h3 className="font-display text-headline-sm text-error">
                  Match Evaluation Failed
                </h3>
                <p className="mt-1 max-w-md text-body-md text-on-surface-variant">
                  {match.failure_code
                    ? `Reason code: ${match.failure_code}. Please verify that the resume and job description have valid extracted content.`
                    : "The matching engine encountered an error while evaluating requirements."}
                </p>
              </div>
              <button
                type="button"
                onClick={load}
                className="mt-2 rounded-xl bg-primary px-5 py-2.5 text-label-md font-semibold text-on-primary"
              >
                Retry Evaluation
              </button>
            </div>
          )}

          {/* Completed Match View */}
          {match.state === "completed" && (
            <div className="flex flex-col gap-8">
              {/* Score Card */}
              <ScoreCard match={match} />

              {/* Requirements & Claim Details Grid */}
              <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
                {/* Left: Requirements Table */}
                <div className="lg:col-span-7">
                  <RequirementTable
                    claims={match.claims}
                    selectedClaimId={selectedClaim?.claim_id}
                    onSelectClaim={(c) => setSelectedClaim(c)}
                    onViewEvidence={handleViewOnDocument}
                  />
                </div>

                {/* Right: Claim Detail Inspector */}
                <div className="lg:col-span-5">
                  <div className="sticky top-20">
                    <ClaimDetail
                      claim={selectedClaim}
                      onViewOnDocument={handleViewOnDocument}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </AsyncState>
  );
}
