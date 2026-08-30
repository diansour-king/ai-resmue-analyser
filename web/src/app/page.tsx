"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

/**
 * The landing page, ported from design/stitch_careerlayer_ai_intelligence/careerlayer_landing_page.
 *
 * The Stitch composition is kept: the underwater video, the dark scrim, the staggered
 * fadeSlideUp cascade, and the badge / heading / body / CTA order.
 *
 * Two deliberate departures from the export:
 *
 * 1. `.ocean-deep` (globals.css) is painted *behind* the video rather than relying on the
 *    video alone. The video is hot-linked from a third-party CDN, so the page has to look
 *    intentional in the seconds before it buffers and in the event it ever 404s. Black is
 *    not a fallback, it is a broken page.
 * 2. The export's nav links — How It Works, Job Matching, For Recruiters — are not here.
 *    Recruiter functionality is a permanent non-goal and the other two have no section to
 *    point at. The nav carries only destinations that exist.
 *
 * The mobile menu is new. "Sign in" was `hidden md:inline-flex`, which left a phone with no
 * way into the product except the CTA.
 *
 * This is the only dark screen in the product. The application is the light ocean
 * experience and the two are never merged.
 */
const VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260622_204221_5339e40b-e73d-4ab0-9c65-79c18c66fd50.mp4";

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);

  // A menu that covers the viewport must not leave the page behind it scrollable.
  useEffect(() => {
    if (!menuOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [menuOpen]);

  return (
    <main className="ocean-deep relative h-screen w-full overflow-hidden">
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        aria-hidden
        className="absolute inset-0 h-full w-full object-cover"
        style={{ objectPosition: "70% center" }}
      >
        <source src={VIDEO_SRC} type="video/mp4" />
      </video>

      <div
        className="pointer-events-none absolute inset-0 hidden md:block"
        style={{
          background:
            "linear-gradient(90deg, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.3) 45%, rgba(0,0,0,0.05) 75%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 md:hidden"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.3) 45%, rgba(0,0,0,0.15) 75%)",
        }}
      />

      {/* Navigation */}
      <nav className="relative z-30 flex items-center justify-between px-6 py-5 md:px-12 lg:px-16">
        <span className="font-display text-lg font-semibold tracking-tight text-white sm:text-xl">
          CareerLayer
        </span>

        <div className="hidden items-center gap-4 md:flex">
          <Link
            href="/login"
            className="font-landing text-sm text-white/80 transition-colors hover:text-white"
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-white px-5 py-2 font-landing text-sm font-medium text-night transition-transform hover:scale-105"
          >
            Get started
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          className="relative z-50 flex h-10 w-10 items-center justify-center text-white transition-transform active:scale-90 md:hidden"
        >
          <span
            className={`material-symbols-outlined absolute select-none transition-all duration-300 ${
              menuOpen ? "rotate-90 scale-75 opacity-0" : "rotate-0 scale-100 opacity-100"
            }`}
          >
            menu
          </span>
          <span
            className={`material-symbols-outlined absolute select-none transition-all duration-300 ${
              menuOpen ? "rotate-0 scale-100 opacity-100" : "-rotate-90 scale-75 opacity-0"
            }`}
          >
            close
          </span>
        </button>
      </nav>

      {/* Mobile menu */}
      <div
        className={`absolute inset-x-0 top-0 z-20 overflow-hidden bg-black/95 backdrop-blur-xl transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] md:hidden ${
          menuOpen ? "h-screen opacity-100" : "pointer-events-none h-0 opacity-0"
        }`}
      >
        <div
          className={`flex h-full flex-col justify-center gap-6 px-8 transition-all delay-100 duration-500 ${
            menuOpen ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"
          }`}
        >
          <Link
            href="/login"
            onClick={() => setMenuOpen(false)}
            className="font-landing text-3xl font-medium text-white/90 transition-colors hover:text-white"
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            onClick={() => setMenuOpen(false)}
            className="inline-flex w-fit items-center gap-2 rounded-full bg-white px-8 py-3.5 font-landing text-base font-medium text-night transition-transform hover:scale-105"
          >
            Analyze my resume
            <span className="material-symbols-outlined select-none text-xl">arrow_forward</span>
          </Link>
        </div>
      </div>

      {/* Hero */}
      <div className="relative z-10 mx-auto flex h-[calc(100vh-80px)] w-full max-w-container-max flex-col justify-between px-6 pb-10 pt-12 sm:pb-12 sm:pt-16 md:px-12 md:pb-16 md:pt-20 lg:px-16">
        <div className="max-w-3xl">
          <div className="mb-4 inline-block animate-fadeSlideUp rounded-full border border-white/30 bg-black/20 px-3 py-1 font-mono text-label-sm text-white backdrop-blur-sm [animation-delay:200ms] [opacity:0] sm:mb-6">
            AI CAREER INTELLIGENCE
          </div>
          <h1 className="animate-fadeSlideUp whitespace-pre-line font-display text-3xl font-medium leading-[1.1] tracking-tight text-white [animation-delay:400ms] [opacity:0] sm:text-5xl md:text-6xl lg:text-7xl">
            {"Understand your\ncareer, with\nintelligence."}
          </h1>
        </div>

        <div>
          <p className="mb-5 max-w-sm animate-fadeSlideUp whitespace-pre-line font-landing text-sm leading-relaxed text-white/70 [animation-delay:700ms] [opacity:0] sm:mb-6 sm:max-w-lg sm:text-base md:text-lg">
            {
              "Turn your resume into an intelligent career profile. Find opportunities that fit, understand your strengths, and discover what to improve next."
            }
          </p>
          <Link
            href="/signup"
            className="inline-flex animate-fadeSlideUp items-center gap-2 rounded-lg bg-white px-5 py-2.5 font-landing text-sm font-medium text-night transition-transform hover:scale-105 [animation-delay:900ms] [opacity:0] sm:px-6 sm:py-3"
          >
            ANALYZE MY RESUME
            <span className="material-symbols-outlined select-none text-base">arrow_forward</span>
          </Link>
        </div>
      </div>
    </main>
  );
}
