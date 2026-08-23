"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { Identity } from "@/lib/types";

/**
 * The application chrome, ported from the Stitch dashboard and evidence screens: a 240px
 * sidebar on desktop, a bottom bar on mobile, and a sticky top bar.
 *
 * The nav lists only what exists. Applications and Jobs were in the Stitch export and were
 * cut as declared non-goals; Job Matches and Skill Gaps arrive with the matching pipeline in
 * phase 3 and are not shown as dead links in the meantime.
 */
const NAV = [
  { href: "/app", label: "Overview", icon: "▦" },
  { href: "/app/resume", label: "Resume", icon: "▤" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    api
      .me()
      .then((me) => {
        setIdentity(me);
        if (!me.onboarded && pathname !== "/app/onboarding") router.replace("/app/onboarding");
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.isUnauthenticated) router.replace("/login");
      })
      .finally(() => setChecked(true));
  }, [pathname, router]);

  if (!checked) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <p aria-busy="true" className="text-body-md text-on-surface-variant">
          Loading…
        </p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-background md:flex-row">
      <nav className="fixed left-0 top-0 z-50 hidden h-screen w-64 flex-col border-r border-outline-variant/30 bg-surface-container-lowest p-4 md:flex">
        <div className="mb-8 flex items-center gap-3 px-2">
          <span className="text-2xl text-primary" aria-hidden>
            ≋
          </span>
          <div>
            <p className="font-display text-headline-md text-primary">CareerLayer</p>
            <p className="text-caption text-on-surface-variant">Career Intelligence</p>
          </div>
        </div>
        <div className="flex flex-1 flex-col gap-2">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-lg border-l-4 px-4 py-3 text-body-md transition-colors ${
                  active
                    ? "border-primary bg-secondary-container font-semibold text-on-secondary-container"
                    : "border-transparent text-on-surface-variant hover:bg-surface-container-high"
                }`}
              >
                <span aria-hidden>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </div>
        <button
          type="button"
          onClick={() => {
            void api.logOut().then(() => router.replace("/"));
          }}
          className="mt-auto rounded-lg px-4 py-3 text-left text-body-md text-on-surface-variant hover:bg-surface-container-high"
        >
          Sign out
        </button>
      </nav>

      <div className="relative flex w-full flex-grow flex-col md:ml-64">
        <header className="sticky top-0 z-40 flex w-full items-center justify-between border-b border-outline-variant/30 bg-surface/80 px-6 py-3 backdrop-blur-xl">
          <span className="font-display text-headline-md text-primary md:hidden">CareerLayer</span>
          <span className="ml-auto text-body-md text-on-surface-variant">
            {identity?.display_name ?? identity?.email}
          </span>
        </header>
        <main className="mx-auto w-full max-w-container-max flex-grow p-4 pb-24 md:p-8">
          {children}
        </main>
      </div>

      <nav className="fixed bottom-0 left-0 z-50 flex w-full items-center justify-around border-t border-outline-variant/30 bg-surface/90 px-4 py-2 backdrop-blur-lg md:hidden">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex w-20 flex-col items-center rounded-xl p-2 ${
                active
                  ? "bg-secondary-container text-on-secondary-container"
                  : "text-on-surface-variant"
              }`}
            >
              <span aria-hidden>{item.icon}</span>
              <span className="mt-1 text-[10px] font-semibold">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
