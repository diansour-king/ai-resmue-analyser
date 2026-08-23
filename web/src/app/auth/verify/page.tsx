"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";

function Verifier() {
  const params = useSearchParams();
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setMessage("That link is missing its token.");
      return;
    }
    api
      .verify(token)
      .then((identity) => {
        router.replace(identity.onboarded ? "/app" : "/app/onboarding");
      })
      .catch((error: unknown) => {
        setMessage(
          error instanceof ApiError
            ? error.message
            : "That sign-in link could not be used.",
        );
      });
  }, [params, router]);

  return (
    <div className="rounded-lg border border-surface-container-high bg-surface-container-lowest p-8 text-center shadow-ocean">
      {message ? (
        <>
          <h1 className="font-display text-headline-md text-on-surface">Link expired</h1>
          <p className="mt-2 text-body-md text-on-surface-variant">{message}</p>
          <a
            href="/login"
            className="mt-6 inline-block rounded-lg bg-primary px-5 py-3 text-label-md text-on-primary"
          >
            Request a new link
          </a>
        </>
      ) : (
        <p aria-busy="true" className="text-body-md text-on-surface-variant">
          Signing you in…
        </p>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-margin-mobile">
      <div className="w-full max-w-md">
        <Suspense fallback={<p className="text-center text-body-md">Signing you in…</p>}>
          <Verifier />
        </Suspense>
      </div>
    </main>
  );
}
