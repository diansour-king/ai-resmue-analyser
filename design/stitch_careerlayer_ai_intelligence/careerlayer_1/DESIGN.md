---
name: CareerLayer
colors:
  surface: '#031427'
  surface-dim: '#031427'
  surface-bright: '#2a3a4f'
  surface-container-lowest: '#000f21'
  surface-container-low: '#0b1c30'
  surface-container: '#102034'
  surface-container-high: '#1b2b3f'
  surface-container-highest: '#26364a'
  on-surface: '#d3e4fe'
  on-surface-variant: '#c4c7c8'
  inverse-surface: '#d3e4fe'
  inverse-on-surface: '#213145'
  outline: '#8e9192'
  outline-variant: '#444748'
  surface-tint: '#c6c6c7'
  primary: '#ffffff'
  on-primary: '#2f3131'
  primary-container: '#e2e2e2'
  on-primary-container: '#636565'
  inverse-primary: '#5d5f5f'
  secondary: '#bec6e0'
  on-secondary: '#283044'
  secondary-container: '#3f465c'
  on-secondary-container: '#adb4ce'
  tertiary: '#ffffff'
  on-tertiary: '#002e6a'
  tertiary-container: '#d8e2ff'
  on-tertiary-container: '#0060ce'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c7'
  on-primary-fixed: '#1a1c1c'
  on-primary-fixed-variant: '#454747'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#d8e2ff'
  tertiary-fixed-dim: '#adc6ff'
  on-tertiary-fixed: '#001a42'
  on-tertiary-fixed-variant: '#004395'
  background: '#031427'
  on-background: '#d3e4fe'
  surface-variant: '#26364a'
typography:
  display-lg:
    fontFamily: Sora
    fontSize: 72px
    fontWeight: '700'
    lineHeight: 80px
    letterSpacing: -0.04em
  display-lg-mobile:
    fontFamily: Sora
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 64px
---

## Brand & Style

The design system is built on the concept of "Depth and Discovery," mirroring the intelligence required to navigate complex career trajectories. It employs a dual-personality approach: a **Cinematic Minimalism** for the marketing experience and a **Structured Modernist** style for the functional application.

The emotional response should transition from awe and curiosity (Landing) to clarity and empowerment (App). The design system balances high-tech precision with organic fluidity, drawing inspiration from the calm, focused environment of a deep-sea observatory.

- **Landing Experience:** High-contrast, immersive, and mysterious. Utilizes large-scale typography and expansive whitespace to allow cinematic background media to breathe.
- **Application Experience:** Efficient, reliable, and transparent. Focuses on information density, logical grouping, and a systematic professional aesthetic.

## Colors

This design system utilizes two distinct palettes to support its dual-mode architecture.

### Cinematic Dark (Landing)
Designed to overlay fluid, underwater video content.
- **Background:** Deep obsidian (#020617) with semi-transparent overlays to maintain legibility over video.
- **Primary Action:** Pure White (#FFFFFF) for high-impact visibility and a premium feel.
- **Accents:** Subtle luminous blues derived from the video content to create a cohesive "underwater" glow.

### Professional Light (App)
Designed for extended focus and data analysis.
- **Background:** Clean White (#FFFFFF) with Soft Slate (#F8FAFC) for secondary containers.
- **Primary Action:** Deep Indigo (#4338CA) or Professional Blue (#2563EB) to signal reliability.
- **Status Colors:** Success (Emerald), Warning (Amber), and Error (Rose) are used with low saturation to maintain a sophisticated tone.

## Typography

The typography strategy emphasizes hierarchy and technical precision.

- **Headlines (Sora):** A geometric sans-serif with a futuristic edge. Used for high-impact marketing copy and primary section headers. Tight letter-spacing is used in display sizes to create a "locked-in" professional look.
- **Body (Hanken Grotesk):** A highly legible, contemporary grotesque. It provides a warm but professional tone for long-form career data and descriptions.
- **Technical Labels (JetBrains Mono):** Used sparingly for metadata, tags, and "intelligence" markers to reinforce the high-tech, data-driven nature of the platform.

For the dark landing page, text should utilize white at 100% for headlines and 80% for body text to reduce eye strain against the cinematic background.

## Layout & Spacing

The design system employs a **12-column fluid grid** for the application and a **centered fixed-width grid** for the landing page.

- **Rhythm:** An 8px linear scale governs all padding and margin decisions. 
- **Landing Page:** Utilizes massive vertical margins (120px+) to create a "cinematic" pacing, allowing users to absorb imagery between content blocks.
- **Application:** Switches to a compact sidebar-driven layout. The "Primary Layer" (main content) is separated from the "Navigation Layer" (sidebar) by a clear 1px border or subtle tonal shift.
- **Responsive Behavior:** On mobile, the 12-column grid collapses to a single column with 16px side margins. Complex data tables in the app should transform into "card stacks" for readability.

## Elevation & Depth

This design system treats the UI as a series of "Layers" (referencing the brand name).

- **Landing Page Depth:** Uses **Glassmorphism**. Surfaces are treated as frosted glass (Backdrop Blur: 20px, Opacity: 10%) to allow the underwater video movement to remain visible behind UI elements.
- **Application Depth:** Uses **Tonal Layering**. Instead of heavy shadows, depth is communicated through background color shifts. Elements "lift" off the page using extremely soft, ambient shadows (15% opacity, 30px blur) with no offset, creating a "floating" effect rather than a "top-down" light source.
- **Interactions:** Hover states on cards should involve a subtle scale increase (1.02x) and a slight increase in shadow diffusion to simulate physical proximity.

## Shapes

The shape language is "Sophisticated Softness."

- **Base Radius:** 8px (0.5rem) is the standard for cards and input fields.
- **Buttons:** Use a slightly higher radius (12px) to make them feel more approachable.
- **Contextual Elements:** Chips and status indicators use a "Pill" shape (full rounding) to contrast against the more structured layout containers.
- **Decorative Elements:** Use large-scale organic blobs or "water droplet" masks for imagery on the landing page to reinforce the aquatic theme.

## Components

### Buttons
- **Primary (Landing):** Ghost style with a thick 2px white border or solid white with black text for maximum contrast.
- **Primary (App):** Solid blue/indigo with white text. High-saturation.
- **Secondary:** Transparent background with a subtle border (#E2E8F0 in light mode).

### Cards
- **Landing:** Borderless, glassmorphic containers with blurred backgrounds.
- **App:** Solid white with a 1px border (#F1F5F9). No heavy shadows.

### Input Fields
- Understated design. In the app, use a subtle light gray fill (#F8FAFC) that turns white on focus with a primary-colored 2px border.

### Career Intelligence Chips
- Small, uppercase labels using `label-sm` (JetBrains Mono). Backgrounds should be low-opacity versions of the status colors (e.g., 10% blue for "In Progress").

### Navigation
- **Top Bar (Landing):** Floating, transparent, becoming glassmorphic on scroll.
- **Sidebar (App):** Permanent, narrow width (240px), utilizing subtle icons and Hanken Grotesk medium for labels.