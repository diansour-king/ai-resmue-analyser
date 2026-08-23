# UI inventory

Derived from the Google Stitch export `stitch_careerlayer_ai_intelligence`, read in full on
2026-08-22. Nothing in this document is inferred from a filename; every component listed was
read in the exported markup and confirmed against the exported screenshot.

The export is committed at `design/stitch_careerlayer_ai_intelligence/`, with the original
archive beside it at `design/stitch_careerlayer_ai_intelligence.zip`. Paths in this document
are relative to that directory. `design/` is a read-only reference: the exported files are
never edited to fit the application.

Source of record: <https://stitch.withgoogle.com/projects/11691017429478219354>

## What the export actually contains

Twelve files. Five screens, each as `code.html` plus `screen.png`, and two design system
definitions.

| Directory | Type | Screen |
| --- | --- | --- |
| `careerlayer_1/DESIGN.md` | Design system | Cinematic Dark, for the landing experience |
| `careerlayer_2/DESIGN.md` | Design system | Professional Light ocean, for the application |
| `careerlayer_landing_page/` | Screen | Marketing hero |
| `careerlayer_dashboard/` | Screen | Overview |
| `careerlayer_evidence_analysis/` | Screen | Resume Analysis, Evidence Grounding |
| `careerlayer_skill_gap_analysis/` | Screen | Skill Gaps |
| `careerlayer_ai_assistant/` | Screen | AI Assistant |

There is no upload screen, no authentication screen, no onboarding, no integrity findings
screen, no job match detail screen, no recruiter screen, and no modal or dialog anywhere in
the export. Section 5 of this document lists what was checked and not found.

## Two design systems, deliberately separate

`careerlayer_1` and `careerlayer_2` are not versions of one system. They are the two halves of
a dual-mode brand and both are authoritative.

| | Landing (`careerlayer_1`) | Application (`careerlayer_2`) |
| --- | --- | --- |
| Background | `#031427` obsidian over video | `#f4fafc` tinted white |
| Primary | `#ffffff` | `#00637c` ocean blue |
| Headline face | Sora | Sora |
| Body face | Hanken Grotesk | Sora |
| Mono face | JetBrains Mono | none |
| Depth | Glassmorphism, 20px backdrop blur | Tonal layers, blue-tinted ambient shadow |
| Container max | 1280px | 1280px |
| Desktop margin | 64px | 48px |
| Mobile margin | 16px | 16px |
| Spacing unit | 8px | 8px |

Both cap content at 1280px and both use an 8px rhythm, so the grid is shared even though the
palettes are not. The two must not be merged.

## Routes

Every `href` in the export is `#`. No screen declares a route. The routes below are derived
from navigation labels, breadcrumbs and page headings, and are marked accordingly.

| Route | Screen | Basis | Designed |
| --- | --- | --- | --- |
| `/` | Landing | Nav item "Home", marked active | yes |
| `/app` | Overview | Sidebar "Overview", marked active on dashboard | yes |
| `/app/resume` | Resume Analysis | Sidebar "Resume", breadcrumb parent "Resume Analysis" | no |
| `/app/resume/evidence` | Evidence Grounding | Breadcrumb leaf, marked active | yes |
| `/app/skill-gaps` | Skill Gaps | Sidebar "Skill Gaps", marked active | yes |
| `/app/assistant` | AI Assistant | Sidebar "AI Assistant", marked active | yes |
| `/app/matches` | Job Matches | Sidebar "Job Matches" | no |
| `/app/jobs` | Jobs | Sidebar "Jobs" | no |
| `/app/applications` | Applications | Sidebar "Applications" | no |
| `/app/settings` | Settings | Sidebar footer | no |
| `/app/help` | Help | Sidebar footer | no |
| `/app/profile` | Profile | Mobile bottom nav only, no sidebar equivalent | no |
| `/how-it-works` | Marketing | Landing nav | no |
| `/job-matching` | Marketing | Landing nav | no |
| `/for-recruiters` | Marketing | Landing nav | no |

Twelve of fifteen implied routes have no design. Three sidebar destinations out of nine are
drawn.

## Navigation

**Landing top bar.** Fixed, transparent, `backdrop-blur-md` over `bg-white/10`, bottom border
`white/10`. Brand wordmark left. Links: Home (active, 2px bottom border), How It Works, Job
Matching, For Recruiters. Ghost "Get Started" button with a 2px white border. Below `md` the
links and button are replaced by a hamburger `menu` icon with no drawer designed. A scroll
listener swaps `bg-white/10` for `bg-white/20` past 50px.

**Application sidebar (desktop, `md` and up).** Fixed, `w-64`, full height,
`bg-surface-container-lowest`, right border `outline-variant/30`. Brand block with a `waves`
icon on the dashboard and a lettermark tile on the evidence screen; the two are not
consistent. Seven primary items with Material Symbols icons: Overview `dashboard`, Resume
`description`, Job Matches `travel_explore`, Jobs `work`, Applications `assignment_turned_in`,
Skill Gaps `trending_up`, AI Assistant `smart_toy`. Two footer items above a top border:
Settings `settings`, Help `help`. Active state is `bg-secondary-container` with a 4px left
`border-primary` and semibold label.

**Application top bar.** Sticky, `bg-surface/80` with `backdrop-blur-xl`. Contents vary by
screen: the dashboard carries a pill search field, notifications and account icons; the
evidence screen replaces search with a breadcrumb trail; skill gaps and the assistant carry
only notifications and account. The assistant additionally shows a hamburger below `md`.

**Application bottom bar (mobile, below `md`).** Fixed, five items, `bg-surface/90` with
`backdrop-blur-lg`, `env(safe-area-inset-bottom)` padding: Home `home`, Resume `description`,
Jobs `work`, Apps `assignment`, Profile `person`. This is a different set from the sidebar:
Job Matches, Skill Gaps and AI Assistant have no mobile entry, and Profile has no desktop
entry. The assistant screen's own comment concedes it highlights "Apps" because no bottom-nav
item matches it.

---

## Screen 1 — Landing

| Field | Value |
| --- | --- |
| Route | `/` |
| Design system | `careerlayer_1` Cinematic Dark |
| Purpose | Brand entry point and the single conversion path into the product |
| Auth | Public |

**Desktop layout.** Full-viewport `<video>` at `z-0`, autoplay, muted, looped, `playsinline`,
`object-cover` at `object-position: 70% center`, sourced from a CloudFront MP4. A horizontal
gradient scrim at `z-[1]` runs `rgba(0,0,0,0.65)` to transparent left to right so the copy
column stays legible while the right side of the footage stays visible. Fixed top bar at
`z-50`. Content at `z-10` in a `max-w-2xl` left-aligned column, vertically centred in
`min-h-screen`, `pt-32 pb-20`. Body is `overflow-hidden`; the page does not scroll.

**Mobile layout.** The scrim switches to a vertical gradient (`0.45` to transparent, top to
bottom). Display type drops from 72px/80px to 40px/48px. Nav links and the CTA button collapse
to a hamburger.

**Components.** Eyebrow chip "AI CAREER INTELLIGENCE" in JetBrains Mono 12px, pill-rounded,
`border-primary/30`, `backdrop-blur-sm bg-black/20`. Three-line display heading "Understand
your / career, with / intelligence." with `whitespace-pre-line` so the line breaks are content,
not reflow. Body paragraph at `text-primary/80`, `max-w-xl`, also `whitespace-pre-line`.
Solid-white CTA "ANALYZE MY RESUME" with a trailing `arrow_forward`, `hover:scale-105`.

**Animation.** One keyframe, `fadeSlideUp`, 1s ease-out forwards, from `opacity 0` /
`translateY(24px)`. Applied as a staggered cascade via `.animate-delay-200` (eyebrow), `400`
(heading), `700` (body), `900` (CTA), each of which sets `opacity: 0` as its initial state.

**Actions.** "Get Started" and "ANALYZE MY RESUME" both lead into the product; neither has a
target in the export. Three nav links point at unbuilt marketing routes.

**Data required.** None. Fully static.

**States.** No loading, empty or error state exists or is needed. The one runtime risk is the
video failing to load or being blocked by a reduced-motion or data-saver preference, for which
no poster image or fallback is specified.

---

## Screen 2 — Overview (dashboard)

| Field | Value |
| --- | --- |
| Route | `/app` |
| Design system | `careerlayer_2` Professional Light |
| Purpose | Landing surface after sign-in, summarising resume analysis and matches |
| Auth | Required |

**Desktop layout.** `md:ml-64` content column beside the fixed sidebar, sticky top bar, main
canvas `p-8` capped at 1280px. Two bands: a four-across KPI row, then a 12-column bento split
7 / 5.

**Mobile layout.** Sidebar hidden, bottom bar shown, KPI row becomes `grid-cols-2`, bento
collapses to one column, main gets `pb-24` to clear the bottom bar. The page heading drops from
`headline-lg` 32px to `headline-lg-mobile` 24px.

**Components and the exact values they display.**

| Component | Rendered content | Field it implies |
| --- | --- | --- |
| Greeting | "Good morning, welcome back." | Time of day, and a user name it does not actually show |
| KPI card 1 | "Resume Intelligence" `82` `/ 100`, 82% fill bar | A composite resume score |
| KPI card 2 | "Job Matches" `24` | Count of match runs |
| KPI card 3 | "Applications" `12` | Count of applications |
| KPI card 4 | "Profile Strength" `87%`, 87% fill bar | A composite profile score |
| Detail card | Four labelled bars: Skills Coverage 79%, Experience Clarity 84%, Evidence Quality 91%, Project Relevance 81% | Four sub-scores |
| Detail card action | "Analyze Again" text button | Re-run extraction and analysis |
| Recent Matches | Three rows: circular score badge, title, "company - location", "View" button | Match run list |
| Recent Matches action | "View All" link | Navigate to `/app/matches` |
| Best Job Match card | Gradient hero, "BEST JOB MATCH", title, "company - location", 94 in a ringed badge, three skill chips, a "Why this match?" prose block, "View Full Details" button | Top match run with a narrative rationale |
| Skills Worth Exploring | Three rows: skill name and a "+N% Match Rate" chip | Counterfactual skill uplift |

Progress bars carry a `progress-pulse` class for the flowing-line animation the design system
describes.

**Actions.** Analyze Again; View per match row; View All; View Full Details; global search;
notifications; account.

**Data required.** Resume composite score and four named sub-scores; match count; application
count; profile strength; a ranked list of match runs each with score, job title, company,
location; a best match with skill chips and a rationale paragraph; a ranked list of absent
skills each with a projected uplift percentage.

**States.** None designed. No skeleton, no zero-resume state, no zero-match state, no error.
A first-time user, who by definition has no resume and no matches, has no designed screen.

**Navigation out.** `/app/matches`, `/app/matches/{id}`, `/app/resume`.

---

## Screen 3 — Evidence Grounding

| Field | Value |
| --- | --- |
| Route | `/app/resume/evidence` |
| Design system | `careerlayer_2` Professional Light |
| Purpose | Show extracted skills alongside the resume text each was read from |
| Auth | Required |

**Desktop layout.** `h-screen overflow-hidden` with a two-pane split inside the content
column: a `flex-[2]` document pane and a fixed `lg:w-[420px]` intelligence panel, each an
independently scrolling rounded card with `ocean-shadow`. Breadcrumb "Resume Analysis >
Evidence Grounding" replaces the search field in the top bar.

**Mobile layout.** `flex-col` below `lg`, so the document pane stacks above the panel, and the
panel loses its fixed width. `pb-24` clears the bottom bar. The header is desktop-only
(`hidden md:flex`), which leaves the mobile breadcrumb unrendered.

**Document pane.** Sticky sub-header with the candidate name, a role and version string
("Senior Software Engineer - v4.2 - Tech Focused"), and a "View Original" button. Below it the
resume is rendered as reflowed semantic HTML: centred name and contact line, a
`flowing-divider`, Professional Summary paragraph, Experience with two roles as `h4` plus
company line plus `ul` of bullets, another divider, and Technical Skills as pill chips. One
bullet fragment carries a highlight `span` with `bg-primary-fixed`, a rounded border and a
hover tooltip reading "View Evidence". A pulsing dot sits in the left gutter of the
highlighted role block.

This pane is HTML text, not a page image. There is no canvas, no image element, no coordinate
system.

**Intelligence panel.** Header with an `analytics` icon and the title "Evidence-Grounded
Intelligence". Body is a scrolling stack of insight cards. The expanded card shows: skill name
with a `code` icon, the subtitle "Verified Skill Extraction", a right-aligned "97%" over the
label "Confidence", a shimmering progress line at 97%, a "DIRECT EVIDENCE" section containing
the quoted resume sentence in a left-bordered box with the matched fragment bolded, and the
attribution "Source: Experience - Page 1". A second, collapsed card shows only "FastAPI" and
"92%" at 60% opacity with a grayscale filter that lifts on hover. Footer holds a full-width
primary button, "Verify All Match Claims".

**Actions.** View Original; click a highlighted span to focus its evidence card; click a
collapsed card to expand it; Verify All Match Claims.

**Data required.** Candidate display name; role title; a resume version label; the resume
content as structured sections (summary, experience entries with title, employer, date range,
bullets, and a skills list); an ordered list of extracted skills each with a confidence
percentage, a verbatim evidence quote, the offsets of the matched fragment within that quote,
and a human-readable source location.

**States.** None designed. No skeleton for a resume still extracting, no state for a resume
with zero extracted skills, no failure state for a document that could not be parsed.

**Navigation out.** "View Original" implies a screen showing the source PDF that does not
exist. "Verify All Match Claims" implies a match result screen that does not exist.

---

## Screen 4 — Skill Gaps

| Field | Value |
| --- | --- |
| Route | `/app/skill-gaps` |
| Design system | `careerlayer_2` Professional Light |
| Purpose | Let the user simulate how acquiring a skill would move their match score |
| Auth | Required |

**Desktop layout.** Scrolling canvas, 1280px cap, `px-48px`, `py-12`. Page heading "What could
improve your match?" at `display` 48px with a supporting paragraph. Below it a 12-column bento
split 7 / 5: visualisation left, controls right, `items-start`.

**Mobile layout.** Single column. The heading has an explicit mobile twin at
`headline-lg-mobile` 24px, toggled by `hidden md:block` / `md:hidden` rather than by a
responsive type scale. Donut shrinks from `w-80` to `w-64`. `pb-32` clears the bottom bar.

**Visualisation.** A `glass-panel` card with two blurred decorative blobs and an inline SVG
donut rotated -90 degrees: a `surface-container-highest` track, a `stroke-primary` arc for the
current score, and a second `stroke-primary-container` arc for the projected addition,
offset to begin where the first ends. Radius 50, stroke width 8, round caps, circumference
314.159. Centre overlay: the caption "PROJECTED MATCH", the animated number, a percent sign,
and a "Base: 78%" pill. Below the donut a result line reads "Select skills to simulate
potential impact." until at least one toggle is on, then becomes "With AWS + Kubernetes: 90%".

**Controls.** Heading "High-Impact Additions" over three toggle rows. Each row is a `label`
containing an icon tile, the skill name, a "+N% impact" caption, and a visually hidden
checkbox driving a custom pill switch. The three rows carry `data-skill` / `data-impact` pairs
of AWS/8, Kubernetes/4, Kafka/2. Below them an info card explains the recommendations come
from "current market demand overlapping with your existing profile strengths".

**Behaviour as exported.** The inline script sums `data-impact` across checked toggles, adds
the sum to a hard-coded `baseScore` of 78, clamps at 100, animates the number over 500ms via
`requestAnimationFrame`, and redraws the second arc. The arithmetic is purely client-side and
strictly additive.

**Actions.** Toggle any subset of skills.

**Data required.** A base match score; a set of candidate skills each with a name, an icon, and
a projected impact; and, to be correct rather than decorative, a way to evaluate a combination
of skills rather than summing them.

**States.** The pre-selection result line is an interaction default, not a data empty state.
There is no state for a user with no gaps, no job selected, or a failed simulation.

**Navigation out.** None. The screen is a leaf.

---

## Screen 5 — AI Assistant

| Field | Value |
| --- | --- |
| Route | `/app/assistant` |
| Design system | `careerlayer_2` Professional Light |
| Purpose | Conversational interface over the user's own resume and match data |
| Auth | Required |

**Desktop layout.** `h-screen` column capped at `max-w-5xl`. Sticky top bar. A fixed heading
block ("CareerLayer Intelligence" plus a one-line subtitle), a `flex-1` scrolling chat feed,
and a pinned composer at the bottom. The top bar's account control is an `img` avatar here
rather than the `account_circle` icon used on the other screens.

**Mobile layout.** Hamburger and wordmark appear in the top bar. Horizontal padding drops to
`px-4`. A 72px spacer block sits below the bottom nav. The assistant has no bottom-nav item of
its own.

**Components.** Three suggested-prompt chips: "Why am I not matching backend jobs?", "Which
skill should I learn first?", "Which jobs fit my experience?". A right-aligned user bubble in
`bg-primary` with an asymmetric radius. An assistant turn consisting of an avatar row
("CareerLayer AI" with a `smart_toy` badge) above a card containing: an "Assessment" heading
with a `lightbulb` icon and a paragraph with inline emphasis; then a two-column bento holding a
"REASON" block, an "EVIDENCE FROM RESUME" block (left-bordered, italic quote, dotted texture
overlay, and a "Page 1, Experience Section" attribution chip), and a "RECOMMENDED ACTION"
block ending in a primary "Update Resume" button. Composer: attach button, auto-growing
`textarea` capped at `max-h-32`, send button. A disclaimer sits below: "AI can make mistakes.
Consider verifying important career advice."

Both `fadeInUp` message entrances are staggered by 150ms.

**Actions.** Send a message; click a suggested prompt; attach a file; "Update Resume".

**Data required.** A conversation of turns; for each assistant turn a structured object with an
assessment, a reason, an evidence quote with a source attribution, and a recommended action
with an optional call to action. This is a structured response, not free markdown, and the card
layout depends on those four fields being present.

**States.** The suggested-prompt row is described in the markup as the pre-conversation state
but is rendered simultaneously with a completed exchange, so the true empty state is not
designed. There is no streaming or typing indicator, no error bubble, and no rate-limit
message.

**Navigation out.** "Update Resume" has no target.

---

## Component census

| Category | Present in export |
| --- | --- |
| Buttons | Ghost bordered (landing), solid primary, solid white on gradient, tonal secondary, text link, icon button, full-width panel button, chip button |
| Forms | Search input (dashboard), chat textarea, three checkbox toggles styled as switches |
| Upload interfaces | None |
| Cards | KPI card with fill bar, detail card, gradient hero card, list card, insight card, collapsed insight card, glass panel, info card, chat response card |
| Tables | None. Every collection is a list or a card stack |
| Charts | One inline SVG donut with two arcs; eight linear progress bars |
| Modals and dialogs | None |
| Tooltips | One, on the highlighted resume span |
| Navigation | Landing top bar, app sidebar, app top bar, mobile bottom bar, breadcrumb |
| Chips | Eyebrow chip, skill pill, impact chip, suggested-prompt chip, source attribution chip |
| Avatars | Icon glyph on three screens, image avatar on one |
| Loading states | None |
| Empty states | None |
| Error states | None |

## Animation and effect inventory

| Name | Where | Definition |
| --- | --- | --- |
| `fadeSlideUp` | Landing, four elements | 1s ease-out, opacity 0 to 1, translateY 24px to 0, staggered 200/400/700/900ms |
| Navbar scroll tint | Landing | `bg-white/10` to `bg-white/20` past 50px scroll |
| `progress-pulse` | Dashboard bars | Class referenced, keyframes not in the export |
| `shimmer` | Evidence confidence bar | 2s infinite translateX sweep |
| `donut-ring` | Skill gaps | Class referenced, keyframes not in the export |
| Score count-up | Skill gaps | 500ms `requestAnimationFrame` interpolation |
| `fadeInUp` | Assistant messages | 0.4s ease-out, 10px rise, 150ms stagger |
| `ambient-glow`, `glass-panel`, `ocean-shadow`, `flowing-divider`, `custom-scrollbar` | Various | Classes referenced; definitions are not in the export and must be reconstructed from the design system prose |

Five utility classes and two keyframe sets are referenced but never defined in the exported
files. They have to be written from the `DESIGN.md` descriptions when the components are
ported.
