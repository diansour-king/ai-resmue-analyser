---
name: CareerLayer
colors:
  surface: '#f4fafc'
  surface-dim: '#d5dbdd'
  surface-bright: '#f4fafc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff5f7'
  surface-container: '#e9eff1'
  surface-container-high: '#e3e9eb'
  surface-container-highest: '#dde3e5'
  on-surface: '#161d1e'
  on-surface-variant: '#3f484d'
  inverse-surface: '#2b3133'
  inverse-on-surface: '#ecf2f4'
  outline: '#6f797d'
  outline-variant: '#bec8cd'
  surface-tint: '#006780'
  primary: '#00637c'
  on-primary: '#ffffff'
  primary-container: '#167d9a'
  on-primary-container: '#f5fbff'
  inverse-primary: '#7dd2f1'
  secondary: '#4e6266'
  on-secondary: '#ffffff'
  secondary-container: '#d0e6eb'
  on-secondary-container: '#54686c'
  tertiary: '#455c78'
  on-tertiary: '#ffffff'
  tertiary-container: '#5e7592'
  on-tertiary-container: '#fafaff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#b9eaff'
  primary-fixed-dim: '#7dd2f1'
  on-primary-fixed: '#001f29'
  on-primary-fixed-variant: '#004d61'
  secondary-fixed: '#d0e6eb'
  secondary-fixed-dim: '#b5cacf'
  on-secondary-fixed: '#0a1e22'
  on-secondary-fixed-variant: '#364a4e'
  tertiary-fixed: '#d1e4ff'
  tertiary-fixed-dim: '#b0c9e8'
  on-tertiary-fixed: '#011d35'
  on-tertiary-fixed-variant: '#314863'
  background: '#f4fafc'
  on-background: '#161d1e'
  surface-variant: '#dde3e5'
typography:
  display:
    fontFamily: Sora
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Sora
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Sora
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Sora
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-md:
    fontFamily: Sora
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.0'
    letterSpacing: 0.01em
  caption:
    fontFamily: Sora
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
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
  margin-desktop: 48px
---

## Brand & Style

The design system is built around the visual metaphor of "The Ascending Ocean." It reflects a journey from the deep, complex depths of job searching to the clarity and calm of professional placement. The personality is intelligent and trustworthy, utilizing a **Corporate Modern** style infused with **Glassmorphism** and **Tactile** elements to prevent it from feeling sterile. 

The user experience should feel like a steady ascent: landing pages utilize deeper saturation and more dramatic gradients, while the core application workspace is airy, bright, and focused. The interface prioritizes breathability and "calm ocean" aesthetics to reduce cognitive load during high-stakes career transitions.

## Colors

The palette is anchored in oceanic transitions. 
- **Primary Accent:** Used for call-to-actions and critical focus states.
- **Surface Strategy:** Backgrounds utilize #F4FAFC to provide a "tinted white" feel that reduces screen glare compared to pure #FFFFFF. Pure white is reserved strictly for elevated card surfaces to create clear depth.
- **Semantic Colors:** Success, Warning, and Error tones are desaturated slightly to maintain the "calm" brand personality while remaining functional.
- **Overlays:** Use semi-transparent versions of #DDF3F8 for hover states to create a "submerged" visual effect.

## Typography

This design system exclusively uses **Sora** to leverage its geometric clarity and distinctive "liquid" feel. 
- **Headlines:** Use tighter letter spacing and lower line heights to maintain a professional, compact appearance.
- **Body Text:** Generous line heights (1.6) are mandatory to ensure readability during long sessions of reviewing resumes or job descriptions.
- **Hierarchy:** Primary Navy (#102A43) is used for all headings to establish authority, while Secondary Text (#526777) is used for descriptions to create a soft visual layer.

## Layout & Spacing

The layout follows a **Fluid Grid** model with a hard cap on content width to maintain readability. 
- **The 8px Rhythm:** All padding, margins, and component heights must be multiples of 8px.
- **Oceanic Flow:** Dividers should not be harsh lines; use "Thin Flowing Dividers"—1px strokes with a linear gradient that fades into the background at the ends, mimicking the horizon line.
- **Desktop:** 12-column grid with 24px gutters.
- **Mobile:** Single column with 16px margins; typography scales down to ensure the "Display" and "Headline-LG" levels do not break layouts.

## Elevation & Depth

Hierarchy is established through **Tonal Layers** and **Ambient Shadows**.
- **The Surface Layer:** The lowest layer is #F4FAFC.
- **The Container Layer:** Interactive areas and secondary content sit on #EAF6FA.
- **The Floating Layer:** Cards and Modals use #FFFFFF and are given depth with "Blue-Tinted Shadows."
- **Shadow Specs:** Shadows use the Primary Navy (#102A43) at very low opacity (4-8%) with a high blur radius (20px+) and a slight Y-offset (4px) to simulate a soft, natural float above a water surface. 
- **Glassmorphism:** Navigation bars and sticky headers should use a 12px backdrop-blur with 80% opacity of the background color to maintain the "liquid" theme.

## Shapes

The shape language is defined by "Round Eight" (0.5rem base). 
- **Base Components:** Buttons and inputs use the standard 8px (0.5rem) radius.
- **Large Containers:** Cards and Modals use 16px (1rem) radius.
- **Wave Elements:** Background decorative elements or section breaks may use large, asymmetrical "subtle wave" curves with a minimum radius of 120px to break the rigidity of the grid.

## Components

- **Buttons:** Primary buttons use a solid Primary Ocean Blue fill. Hover states should trigger a subtle aqua glow (inner shadow) and a 2px upward shift.
- **Chips:** Used for job categories or skills. They feature a light blue background (#DDF3F8) with navy text and no border.
- **Cards:** White backgrounds, soft blue shadows, and 16px internal padding. Card borders should be 1px solid #EAF6FA for subtle definition.
- **Input Fields:** Use #FFFFFF backgrounds with a 1px #DDF3F8 border. On focus, the border transitions to Primary Ocean Blue with a soft 4px outer glow.
- **Progress Indicators:** Use "Flowing Lines"—horizontal progress bars that utilize a subtle pulse animation to suggest movement through the ocean.
- **Lists:** List items should have a 1px "Flowing Divider" between them, stopping 16px before the edge of the container.