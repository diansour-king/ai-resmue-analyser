import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "CareerLayer",
  description:
    "An auditable resume screening engine that can prove what it read, where it read it, and whether anything in the document was trying to manipulate the reader.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* next/font/google is the better option here: it self-hosts the files and removes
            this render-blocking request. It fetches from Google at build time, which the
            build environment this was verified in cannot reach, so the linked stylesheet
            from the Stitch export is kept. Switching is a two-line change once the build
            host has network access to fonts.googleapis.com. */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font -- app router: this head
            is the document head, not a per-page one, so the rule does not apply. */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@500&family=Sora:wght@400;600;700&display=swap"
        />
        {/* Material Symbols Outlined — the icon set the Stitch screens are drawn with.
            display=block, not swap: an icon font must not flash its ligature names
            ("dashboard", "description") as fallback text while it loads. */}
        {/* eslint-disable-next-line @next/next/no-page-custom-font, @next/next/google-font-display */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
