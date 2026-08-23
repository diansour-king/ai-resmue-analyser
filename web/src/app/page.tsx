import Link from "next/link";

/**
 * The landing page, ported from design/stitch_careerlayer_ai_intelligence/careerlayer_landing_page.
 *
 * Deliberately unchanged: the dark cinematic composition, the gradient scrim over the video,
 * the staggered fadeSlideUp cascade and the navigation style are all as approved. The only
 * edits are turning the two dead buttons into real links.
 *
 * This is the only dark screen in the product. The application is the light ocean experience
 * and the two are never merged.
 */
export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-night text-night-on-surface">
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        poster="/landing-poster.jpg"
        className="absolute inset-0 z-0 h-full w-full object-cover"
        style={{ objectPosition: "70% center" }}
      >
        <source src="/landing.mp4" type="video/mp4" />
      </video>

      <div
        className="pointer-events-none absolute inset-0 z-[1] hidden md:block"
        style={{
          background:
            "linear-gradient(90deg, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.25) 45%, rgba(0,0,0,0) 75%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 z-[1] md:hidden"
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.45) 0%, rgba(0,0,0,0.18) 45%, rgba(0,0,0,0) 75%)",
        }}
      />

      <nav className="fixed top-0 z-50 w-full border-b border-white/10 bg-white/10 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-container-max items-center justify-between px-margin-mobile py-6 md:px-[64px]">
          <div className="font-display text-headline-md font-bold text-white">CareerLayer</div>
          <Link
            href="/login"
            className="hidden items-center justify-center rounded border-2 border-white px-6 py-3 font-landing text-body-lg font-medium text-white transition-colors hover:bg-white hover:text-night md:inline-flex"
          >
            Sign in
          </Link>
        </div>
      </nav>

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-container-max flex-col justify-center px-margin-mobile pb-20 pt-32 md:px-[64px]">
        <div className="max-w-2xl text-left">
          <div className="mb-6 inline-block animate-fadeSlideUp rounded-full border border-white/30 bg-black/20 px-3 py-1 font-mono text-label-sm text-white backdrop-blur-sm [animation-delay:200ms] [opacity:0]">
            AI CAREER INTELLIGENCE
          </div>
          <h1 className="mb-6 animate-fadeSlideUp whitespace-pre-line font-display text-display-lg-mobile text-white [animation-delay:400ms] [opacity:0] md:text-display-lg">
            {"Understand your\ncareer, with\nintelligence."}
          </h1>
          <p className="mb-10 max-w-xl animate-fadeSlideUp whitespace-pre-line font-landing text-body-lg text-white/80 [animation-delay:700ms] [opacity:0]">
            {
              "Turn your resume into an intelligent career\nprofile. Find opportunities that fit, understand\nyour strengths, and discover what to improve\nnext."
            }
          </p>
          <Link
            href="/signup"
            className="inline-flex animate-fadeSlideUp items-center justify-center rounded bg-white px-8 py-4 font-landing text-body-lg font-medium text-night transition-transform duration-200 hover:scale-105 [animation-delay:900ms] [opacity:0]"
          >
            ANALYZE MY RESUME
          </Link>
        </div>
      </div>
    </main>
  );
}
