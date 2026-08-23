import type { ReactNode } from "react";

import { ApiError } from "@/lib/api";

/**
 * The four states every screen that loads something has to render.
 *
 * One component rather than four ad hoc spinners, so no screen can quietly ship without an
 * empty state or an error state.
 */
export function AsyncState({
  loading,
  error,
  isEmpty,
  emptyTitle,
  emptyBody,
  onRetry,
  children,
}: {
  loading: boolean;
  error: unknown;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyBody?: string;
  onRetry?: () => void;
  children: ReactNode;
}) {
  if (loading) return <Skeleton />;

  if (error) {
    const apiError = error instanceof ApiError ? error : null;
    return (
      <div
        role="alert"
        className="rounded-lg border border-error-container bg-error-container/40 p-6"
      >
        <p className="font-display text-headline-md text-on-error-container">
          That did not load
        </p>
        <p className="mt-2 text-body-md text-on-surface-variant">
          {apiError?.message ?? "Something went wrong."}
        </p>
        {apiError?.requestId ? (
          <p className="mt-2 font-mono text-caption text-on-surface-variant">
            Reference {apiError.requestId}
          </p>
        ) : null}
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 rounded-lg bg-primary px-4 py-2 text-label-md text-on-primary"
          >
            Try again
          </button>
        ) : null}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="rounded-lg border border-surface-container-high bg-surface-container-lowest p-10 text-center">
        <p className="font-display text-headline-md text-on-surface">
          {emptyTitle ?? "Nothing here yet"}
        </p>
        {emptyBody ? (
          <p className="mx-auto mt-2 max-w-md text-body-md text-on-surface-variant">{emptyBody}</p>
        ) : null}
      </div>
    );
  }

  return <>{children}</>;
}

function Skeleton() {
  return (
    <div aria-busy="true" aria-label="Loading" className="space-y-3">
      {[0, 1, 2].map((row) => (
        <div
          key={row}
          className="h-16 animate-pulse rounded-lg bg-surface-container"
          style={{ animationDelay: `${row * 120}ms` }}
        />
      ))}
    </div>
  );
}
