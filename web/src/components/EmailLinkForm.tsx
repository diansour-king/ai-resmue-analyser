"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { ApiError, api } from "@/lib/api";

/**
 * Sign-in and sign-up are the same interaction: type an email, receive a one-time link.
 *
 * There is no password field because the system stores no passwords. In development the API
 * returns the link so the flow works without a mail server, and it is shown here rather than
 * hidden in a log.
 */
export function EmailLinkForm({
  mode,
  title,
  subtitle,
  footer,
}: {
  mode: "login" | "signup";
  title: string;
  subtitle: string;
  footer: ReactNode;
}) {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const result = mode === "signup" ? await api.signUp(email) : await api.logIn(email);
      setSent(true);
      setDevLink(result.login_url);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "That did not work.");
    } finally {
      setSending(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-margin-mobile">
      <div className="w-full max-w-md">
        <Link href="/" className="mb-8 block font-display text-headline-md text-primary">
          CareerLayer
        </Link>
        <div className="rounded-lg border border-surface-container-high bg-surface-container-lowest p-8 shadow-ocean">
          <h1 className="font-display text-headline-md text-on-surface">{title}</h1>
          <p className="mt-2 text-body-md text-on-surface-variant">{subtitle}</p>

          {sent ? (
            <div className="mt-6" aria-live="polite">
              <p className="text-body-md text-on-surface">
                Check <span className="font-semibold">{email}</span> for your sign-in link.
              </p>
              {devLink ? (
                <a
                  href={devLink}
                  className="mt-4 block break-all rounded-lg bg-secondary-container p-3 font-mono text-caption text-on-secondary-container"
                >
                  Development link: {devLink}
                </a>
              ) : null}
            </div>
          ) : (
            <form onSubmit={submit} className="mt-6 space-y-4">
              <label className="block">
                <span className="text-label-md text-on-surface-variant">Email</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  className="mt-1 w-full rounded-lg border border-surface-container-highest bg-surface-container-lowest px-4 py-3 text-body-md outline-none focus:border-primary focus:ring-4 focus:ring-primary-fixed/50"
                />
              </label>
              <button
                type="submit"
                disabled={sending}
                className="w-full rounded-lg bg-primary px-4 py-3 text-label-md text-on-primary transition-colors hover:bg-primary-container disabled:opacity-60"
              >
                {sending ? "Sending…" : "Email me a link"}
              </button>
              {error ? (
                <p role="alert" className="text-body-md text-error">
                  {error}
                </p>
              ) : null}
            </form>
          )}
        </div>
        <div className="mt-6 text-center">{footer}</div>
      </div>
    </main>
  );
}
