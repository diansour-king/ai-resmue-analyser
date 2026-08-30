"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Icon } from "@/components/Icon";
import { ApiError, api } from "@/lib/api";
import type { Identity } from "@/lib/types";

/**
 * The application chrome, ported from the Stitch dashboard and evidence screens: a 256px
 * sidebar on desktop, a bottom bar on mobile, and a sticky glass top bar.
 *
 * The nav lists only what exists. Applications, Jobs browsing and the AI assistant were in
 * the Stitch export and were cut as declared non-goals, so they are not shown as dead
 * links. The Stitch top-bar search and notification bell are omitted for the same reason —
 * there is nothing behind them yet.
 */
const NAV = [
  { href: "/app", label: "Overview", icon: "dashboard" },
  { href: "/app/resume", label: "Resume", icon: "description" },
  { href: "/app/jobs", label: "Job Descriptions", icon: "work" },
  { href: "/app/matches", label: "Matches", icon: "compare_arrows" },
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
        <p aria-busy="true" className="flex items-center gap-2 text-body-md text-on-surface-variant">
          <Icon name="progress_activity" className="animate-spin text-xl" />
          Loading…
        </p>
      </div>
    );
  }

  const isActive = (href: string) =>
    href === "/app" ? pathname === "/app" : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className="flex min-h-screen flex-col bg-surface-bright md:flex-row">
      {/* Desktop sidebar */}
      <nav className="fixed left-0 top-0 z-50 hidden h-screen w-64 flex-col border-r border-outline-variant/30 bg-surface-container-lowest p-4 md:flex">
        <div className="mb-8 flex items-center gap-3 px-2">
          <Icon name="waves" filled className="text-3xl text-primary" />
          <div>
            <p className="font-display text-headline-md leading-none text-primary">CareerLayer</p>
            <p className="mt-1 text-caption text-on-surface-variant">Career Intelligence</p>
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-lg border-l-4 px-4 py-3 text-body-md transition-all duration-200 ${
                  active
                    ? "border-primary bg-secondary-container font-semibold text-on-secondary-container"
                    : "border-transparent text-on-surface-variant hover:bg-surface-container-high"
                }`}
              >
                <Icon name={item.icon} filled={active} className="text-xl" />
                {item.label}
              </Link>
            );
          })}
        </div>

        <div className="mt-auto border-t border-outline-variant/30 pt-3">
          <button
            type="button"
            onClick={() => void api.logOut().then(() => router.replace("/"))}
            className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left text-body-md text-on-surface-variant transition-colors hover:bg-surface-container-high"
          >
            <Icon name="logout" className="text-xl" />
            Sign out
          </button>
        </div>
      </nav>

      {/* Main column */}
      <div className="relative flex w-full flex-grow flex-col md:ml-64">
        <header className="glass-panel sticky top-0 z-40 flex w-full items-center gap-4 border-b border-outline-variant/30 px-4 py-3 md:px-6">
          <span className="flex items-center gap-2 font-display text-headline-md text-primary md:hidden">
            <Icon name="waves" filled />
            CareerLayer
          </span>
          <div className="ml-auto">
            <AccountMenu identity={identity} onSignOut={() => void api.logOut().then(() => router.replace("/"))} />
          </div>
        </header>

        <main className="mx-auto w-full max-w-container-max flex-grow p-4 pb-24 md:p-8">
          {children}
        </main>
      </div>

      {/* Mobile bottom bar */}
      <nav className="glass-panel fixed bottom-0 left-0 z-50 flex w-full items-center justify-around border-t border-outline-variant/30 px-2 py-2 md:hidden">
        {NAV.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={`flex w-[72px] flex-col items-center gap-0.5 rounded-xl py-1.5 transition-colors ${
                active ? "bg-secondary-container text-on-secondary-container" : "text-on-surface-variant"
              }`}
            >
              <Icon name={item.icon} filled={active} className="text-xl" />
              <span className="text-[10px] font-semibold">{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

function AccountMenu({
  identity,
  onSignOut,
}: {
  identity: Identity | null;
  onSignOut: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const name = identity?.display_name ?? identity?.email ?? "Account";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-full border border-outline-variant/30 bg-surface-container py-1.5 pl-3 pr-1.5 text-label-md text-on-surface transition-colors hover:border-primary/40"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="hidden max-w-[180px] truncate sm:block">{name}</span>
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-on-primary">
          <Icon name="person" filled className="text-lg" />
        </span>
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-56 rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-1.5 shadow-ocean-float"
        >
          <div className="border-b border-outline-variant/30 px-3 py-2">
            <p className="truncate text-label-md text-on-surface">{identity?.display_name ?? "Signed in"}</p>
            <p className="truncate text-caption text-on-surface-variant">{identity?.email}</p>
          </div>
          <button
            type="button"
            onClick={onSignOut}
            className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-body-md text-on-surface-variant transition-colors hover:bg-surface-container-high"
            role="menuitem"
          >
            <Icon name="logout" className="text-lg" />
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
