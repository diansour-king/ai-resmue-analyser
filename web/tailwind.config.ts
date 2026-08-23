import type { Config } from "tailwindcss";

// Both palettes come verbatim from design/stitch_careerlayer_ai_intelligence:
// careerlayer_1 (Cinematic Dark, landing) is prefixed `night`, careerlayer_2
// (Professional Light ocean, application) keeps the unprefixed Material token names the
// exported markup already uses. They are two halves of one brand and are never merged.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#f4fafc",
        "surface-dim": "#d5dbdd",
        "surface-bright": "#f4fafc",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#eff5f7",
        "surface-container": "#e9eff1",
        "surface-container-high": "#e3e9eb",
        "surface-container-highest": "#dde3e5",
        "on-surface": "#161d1e",
        "on-surface-variant": "#3f484d",
        "inverse-surface": "#2b3133",
        "inverse-on-surface": "#ecf2f4",
        outline: "#6f797d",
        "outline-variant": "#bec8cd",
        primary: "#00637c",
        "on-primary": "#ffffff",
        "primary-container": "#167d9a",
        "on-primary-container": "#f5fbff",
        "inverse-primary": "#7dd2f1",
        secondary: "#4e6266",
        "on-secondary": "#ffffff",
        "secondary-container": "#d0e6eb",
        "on-secondary-container": "#54686c",
        tertiary: "#455c78",
        "on-tertiary": "#ffffff",
        error: "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",
        "primary-fixed": "#b9eaff",
        "primary-fixed-dim": "#7dd2f1",
        background: "#f4fafc",
        "on-background": "#161d1e",
        "surface-variant": "#dde3e5",
        night: "#031427",
        "night-container": "#102034",
        "night-on-surface": "#d3e4fe",
        "night-on-surface-variant": "#c4c7c8",
      },
      fontFamily: {
        display: ["Sora", "system-ui", "sans-serif"],
        body: ["Sora", "system-ui", "sans-serif"],
        landing: ["Hanken Grotesk", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        display: ["48px", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "700" }],
        "display-lg": ["72px", { lineHeight: "80px", letterSpacing: "-0.04em", fontWeight: "700" }],
        "display-lg-mobile": ["40px", { lineHeight: "48px", letterSpacing: "-0.02em", fontWeight: "700" }],
        "headline-lg": ["32px", { lineHeight: "1.2", fontWeight: "600" }],
        "headline-lg-mobile": ["24px", { lineHeight: "1.2", fontWeight: "600" }],
        "headline-md": ["24px", { lineHeight: "1.3", fontWeight: "600" }],
        "body-lg": ["18px", { lineHeight: "1.6" }],
        "body-md": ["16px", { lineHeight: "1.6" }],
        "label-md": ["14px", { lineHeight: "1.0", letterSpacing: "0.01em", fontWeight: "600" }],
        caption: ["12px", { lineHeight: "1.4" }],
        "label-sm": ["12px", { lineHeight: "16px", letterSpacing: "0.05em", fontWeight: "500" }],
      },
      borderRadius: { DEFAULT: "0.5rem", md: "0.75rem", lg: "1rem", xl: "1.5rem" },
      spacing: { gutter: "24px", "margin-mobile": "16px", "margin-desktop": "48px" },
      maxWidth: { "container-max": "1280px" },
      boxShadow: {
        ocean: "0 4px 20px rgba(16, 42, 67, 0.06)",
        "ocean-float": "0 6px 28px rgba(16, 42, 67, 0.08)",
      },
      keyframes: {
        fadeSlideUp: {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: { fadeSlideUp: "fadeSlideUp 1s ease-out forwards" },
    },
  },
  plugins: [],
};

export default config;
