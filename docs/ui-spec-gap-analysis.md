# UI and specification gap analysis

Compares the Stitch export against sections 2 to 14 of the CareerLayer build specification.
Nothing here changes the architecture. Each item states what the two sources say and what
decision it forces.

The headline: **the Stitch design covers the career-advice product well and covers the
integrity product not at all.** The differentiator named in section 2 has zero pixels.

---

## A. Specification features that already have UI

| Spec reference | Feature | Where it appears | Fidelity |
| --- | --- | --- | --- |
| 2 | Product positioning and brand | Landing hero, both `DESIGN.md` files | Complete |
| 3, 4 | Nothing UI-facing | | |
| 7.1 | Dual extraction, as a concept | Evidence panel's "Verified Skill Extraction" | Conceptual only. The screen shows one read, not two |
| 9.4 | Every satisfied claim cites a span | Evidence panel quote plus "Source: Experience - Page 1"; highlighted span in the document pane | Partial. Cites a section and page, not a span with coordinates |
| 10 | Findings are explainable in plain language | Evidence card layout, assistant's Reason and Evidence blocks | Pattern exists and is reusable for findings |
| 10 | No auto-reject | Satisfied trivially: no reviewer or bulk action exists anywhere | Complete by absence |
| 2 | Match analysis with a rationale | Dashboard "Why this match?" block | Partial. Prose only, one paragraph, no requirement breakdown |
| 7.3 | Counterfactual framing | Skill Gaps donut and toggles | Wrong counterfactual. See D6 |

Four of the nine product concepts listed in step 7 of the brief have a designed home:
resume analysis, evidence-grounded claims, skill-gap analysis, and career intelligence.
Five do not: dual extraction, integrity detection, job matching detail, explainable match
scoring, and counterfactual impact analysis in the spec's sense.

---

## B. Specification features with no UI at all

Ordered by how badly the missing screen blocks the build.

### B1. Resume upload. Blocks Phase 2.

Section 8 defines `POST /v1/resumes` as a multipart upload; Phase 2's done-criteria is "you can
upload a PDF in the browser". The export contains no file input, no drop zone, no progress
indicator, no file-type or size-limit messaging, and no post-upload confirmation. The landing
CTA "ANALYZE MY RESUME" and the dashboard's "Analyze Again" both point at `#`.

Every screen in the export presents a resume that already exists. The act of putting one there
is undesigned.

### B2. Integrity findings. Blocks the product's reason for existing.

Sections 7.2 and 10 require findings surfaced with severity, exact text, page, location and a
plain-language reason, for eight detectors. The data model has a `findings` table with
`detector_id`, `severity`, `confidence`, `page`, `bbox`, `excerpt`, `rationale`.

None of this renders anywhere. There is no findings list, no severity indicator, no detector
attribution, no "suspicious" or "high" treatment, no review affordance. A resume with three
high-severity injections and a clean resume are the same screen.

This is the single largest gap in the audit.

### B3. Page-render document viewer with bbox overlay. Blocks Phase 2's done-criteria.

Section 8 defines `GET /v1/resumes/{id}/pages/{n}` returning a PNG. Phase 2 requires "findings
overlaid on their bounding boxes" and a side-by-side "what a human sees / what the machine
reads".

The evidence screen renders reflowed HTML text. There is no image, no coordinate space, no
overlay layer, no page navigation, no zoom, no dual-pane comparison. See D2, which is the
harder version of this problem.

### B4. Job description ingestion. Blocks Phase 3.

Section 8 defines `POST /v1/jobs` to create a job description and extract requirements. There
is no paste field, no URL field, no requirement review screen, and no way to see the extracted
`requirements` rows with their `kind` and `weight`.

The sidebar's "Jobs" item suggests browsing a catalogue, which is the opposite operation and a
declared non-goal. See C2.

### B5. Match result detail. Blocks Phase 3's done-criteria.

Phase 3 requires "every satisfied requirement is clickable and highlights its source text".
There is no screen listing requirements with met/unmet status, per-claim confidence, weight, or
click-through to evidence. The dashboard's "View Full Details" and the evidence panel's "Verify
All Match Claims" both point at this missing screen.

### B6. Impact canary result. Blocks Phase 4.

Section 7.3 makes `impact_delta` the headline number of the integrity report, and section 6
stores `score` and `score_without_flagged` on `match_runs`. No screen shows a delta, a
before/after pair, or which requirements moved.

### B7. Authentication. Blocks Phase 2.

Section 4 specifies Auth.js with an email magic link. There is no sign-in screen, no email
entry, no "check your inbox" screen, no expired-link screen, and no signed-out state on any
application screen. "Get Started" has no destination.

### B8. Match progress. Blocks Phase 3.

Section 8 defines `GET /v1/matches/{id}/events` as an SSE stream because scoring takes time.
Nothing in the export represents an in-flight job: no progress bar, no stage labels, no
cancel.

### B9. Loading, empty and error states. Blocks every phase.

Not one of the five screens has any of the three. Specifically missing:

- Skeletons for the dashboard KPIs, the match list, the evidence panel and the chat feed
- First-run empty state: a user with no resume has no designed dashboard
- Zero-match, zero-finding and zero-gap states
- Extraction failure, matching the `ExtractionFailed` and `OcrUnavailable` exceptions
- `429` rate-limit messaging with `Retry-After`, required by section 8
- The daily cost-ceiling cutoff from Phase 5
- Upload rejection for oversize files, over-page-count files, and files that are not PDFs

### B10. Auditability surface.

Section 6 defines an `audit_log` table and the positioning line in section 2 promises the
system "can prove what it read". Nothing displays an audit trail, a prompt version, a model
identifier, or an extraction method.

---

## C. UI that exists in Stitch but is not in the specification

### C1. Applications. Contradicts section 13.

A sidebar item, a mobile bottom-nav item, and a dashboard KPI reading "12". The specification
says CareerLayer "is not an ATS" and "does not manage a hiring pipeline", and section 13 lists
recruiter and workspace features as non-goals. The data model has no applications table and no
place to put one.

### C2. Jobs browse and global search. Contradicts section 13.

A "Jobs" sidebar item, a "Jobs" mobile item, and a search field in the dashboard top bar.
Section 13 forbids "job board scraping or integrations". `job_descriptions` rows are created by
the user for a single match; they are not a browsable, searchable catalogue, and there is no
search endpoint in section 8.

### C3. AI Assistant. Not forbidden, but entirely unscoped.

A full conversational surface with structured responses, suggested prompts, file attachment,
and a "Update Resume" action. It appears nowhere in sections 2 to 14: no phase owns it, no
tables back it, no endpoint serves it, and no cost ceiling covers it. It is the most expensive
screen in the export per user session and the least specified.

Note also that a chat interface over resume content is the same untrusted-input problem as the
matching pipeline, and section 9's four structural rules would have to apply to it too.

### C4. Composite scores. Contradicts section 10.

"Resume Intelligence 82/100", "Profile Strength 87%", "Skills Coverage 79%", "Experience
Clarity 84%", "Evidence Quality 91%", "Project Relevance 81%".

Six numbers, no definitions. Section 10 requires "No opaque risk scores" and that every finding
show "the exact text, the page, the location, and a plain-language reason". These six are
precisely opaque scores, and they are the first thing a user sees. See D1.

### C5. Market-demand recommendations.

The skill-gap info card attributes recommendations to "current market demand". No data source
for market demand exists in the specification, the data model, or the stack. Section 13 forbids
job board integrations, which is where such data would come from.

### C6. Settings, Help, Profile, notifications.

Four destinations with no specification coverage. Low risk, but four more routes.

### C7. Resume versioning.

The evidence screen shows "v4.2 - Tech Focused". The model stores one `filename` per resume row
and a `sha256` unique per user. There is no version number, no label, and no lineage.

### C8. Marketing routes.

"How It Works", "Job Matching", "For Recruiters" imply three more pages that were not exported.

---

## D. Direct contradictions

### D1. The dashboard is the generic SaaS dashboard the brief forbids.

Step 7 of the brief says the product must not become a generic SaaS admin dashboard, and step 8
says findings must be explainable and evidence must be shown. The Overview screen is four KPI
tiles, four unexplained progress bars, and a list — the canonical admin dashboard, and its
numbers are exactly the opaque scores section 10 rules out.

The screen is well drawn. The problem is what it chooses to say.

**Options.** Keep the layout and replace the metrics with ones that are defined and defensible:
extraction method used, pages processed, findings by severity, requirements met with evidence
versus asserted without, impact delta on the last match. That preserves the Stitch composition
and the visual language exactly while making every number traceable. Alternatively define the
six composites rigorously and publish the formulas, which is more work and still leaves a
number nobody can check by eye.

Recommendation: reuse the composition, change the payload. This needs your decision because it
changes what the approved screen says, even though it does not change how it looks.

### D2. The document viewer is text; the specification needs pixels.

The evidence pane renders semantic HTML with a CSS highlight. The specification's viewer needs
a 200 DPI page raster with findings drawn on `spans.bbox` coordinates.

These are not the same component and cannot be the same component. The whole point of the
integrity engine is that the text layer and the rendered layer disagree; showing only reflowed
text shows only the machine's read, which is the side an adversary controls. A hidden-text
injection is invisible in the evidence pane by construction — the text is there in the HTML,
looking exactly like every other bullet.

**This is the most important finding in the audit.** The approved evidence screen cannot
demonstrate the product's core claim, and no amount of styling fixes it.

**Options.** Add a third view mode to the existing two-pane frame — the pane already scrolls
independently and has a "View Original" button that currently goes nowhere, so a page-render
view with an overlay fits the approved layout without redesigning it. Or design a separate
integrity screen. The first respects step 6 and step 9 better.

### D3. Evidence attribution granularity.

The UI says "Source: Experience - Page 1". The model stores `page`, `bbox`, `char_start`,
`char_end` — and it stores no section names. Nothing in the extraction pipeline identifies that
a span belongs to an "Experience" section.

Either the UI drops to "Page 1" plus a click-to-locate, or section detection becomes a new
extraction concern. The former is cheaper and loses little.

### D4. Skill confidence exists outside any match run.

The evidence panel shows "Python 97% confidence" with no job description in view. In the data
model, `claims.confidence` belongs to a `claim`, which belongs to a `match_run`, which requires
a `job_description_id`. A skill confidence detached from a job is not a thing the schema can
express.

Either the screen scopes to a selected job, or a new resume-level skill extraction table is
introduced. The second is a real addition, not a rename.

### D5. Skill Gaps shows a match score with no job attached.

Same shape as D4. "Projected Match 78%" against what? `match_runs.score` is per
resume-and-job-description pair. The screen has no job selector.

### D6. The skill-gap simulator computes a fabricated number.

The exported script does `newScore = min(78 + sum(checked impacts), 100)`. Real scoring is
claim-weighted: two skills can satisfy the same requirement, so their effects are not additive,
and a skill can satisfy a requirement only partially. Shipping this arithmetic puts a number on
screen that the backend cannot reproduce, which violates section 9.3's rule that scores must be
reconstructible.

The interaction design is good and worth keeping. The computation has to move to the server:
each toggle change requests a re-scored counterfactual, or the server precomputes the score for
each subset the UI can produce (three toggles is eight combinations, so precomputing is
entirely practical).

### D7. "Update Resume" versus "not a resume rewriter".

Section 2 says CareerLayer "reports; it does not ghostwrite". The assistant's recommended-action
button says "Update Resume" directly beneath advice about what to add.

If it navigates to re-upload, it is fine and the label is misleading. If it drafts content, it
violates a stated product constraint. Needs a one-word decision from you; my read is that
"Upload a new version" says the same thing without the ambiguity.

### D8. "For Recruiters" versus "not an ATS".

The landing nav advertises a recruiter audience. Section 2 says CareerLayer is not an ATS,
section 13 lists recruiter features as a non-goal, and section 10 forbids the reject-flow that
a recruiter product would imply.

The link is one word in an approved header, so I have not touched it, but it promises a product
that the specification says will not be built.

### D9. Mobile navigation contradicts desktop navigation.

The sidebar has nine destinations, the bottom bar has five, and only three overlap. Job
Matches, Skill Gaps and AI Assistant are unreachable on mobile; Profile is unreachable on
desktop. The assistant screen's own markup comments on this and picks an unrelated item to
highlight.

### D10. Two inconsistent brand marks.

The dashboard uses a `waves` glyph beside the wordmark; the evidence screen uses a lettermark
tile; skill gaps and the assistant use neither. One of the three has to win.

---

## E. Data the UI needs that the current model cannot provide

Straight against section 6.

| UI element | Screen | Model support | Verdict |
| --- | --- | --- | --- |
| Resume Intelligence 82/100 | Overview | None | New computation, undefined |
| Profile Strength 87% | Overview | None | New computation, undefined |
| Skills Coverage, Experience Clarity, Evidence Quality, Project Relevance | Overview | None | Four new computations, undefined |
| Applications count and list | Overview, nav | No table | Out of scope per section 13 |
| Job Matches count | Overview | `count(match_runs)` | Supported |
| Match list rows: score, title, company | Overview | `match_runs.score`, `job_descriptions.title/company` | Supported |
| Match row location ("Remote", "New York, NY") | Overview | No column | Add `job_descriptions.location` |
| Best match skill chips | Overview | `requirements.text` where `kind = hard_skill` | Supported with a query |
| "Why this match?" paragraph | Overview | No column | Add a narrative field on `match_runs`, schema-constrained per section 9.2 |
| Greeting name | Overview | `users` has `email` only | Add `display_name` |
| Skill uplift "+8% Match Rate" | Overview, Skill Gaps | No table | New counterfactual computation and storage |
| Market demand basis | Skill Gaps | No source | No data source exists; either drop the claim or find one |
| Base score with no job | Skill Gaps | `match_runs` requires a job | Needs a job selector or a new concept |
| Skill name plus confidence, no job | Evidence | `claims` require a `match_run` | Needs a resume-level extraction table |
| Evidence quote with inner highlight offsets | Evidence | `spans.char_start/char_end` | Supported |
| "Source: Experience - Page 1" | Evidence | `spans.page` yes, section name no | Drop the section, or add section detection |
| Resume version "v4.2 - Tech Focused" | Evidence | No version or label column | Add, or drop from the UI |
| Candidate display name and role | Evidence | Not extracted | Extraction concern, currently unspecified |
| Structured resume sections for rendering | Evidence | `extractions.raw_text` and `spans` are flat | Section segmentation is not in the pipeline |
| Chat turns and threads | Assistant | No tables | Two new tables if the screen ships |
| Assistant structured response fields | Assistant | None | New Pydantic schema per section 9.2 |
| Notification list | All | No table | Out of scope |
| Global search results | Overview | No endpoint | Out of scope per section 13 |
| Findings with severity and bbox | Nowhere | `findings` fully supports it | Model is ready; the UI is missing |
| `impact_delta` | Nowhere | `match_runs` supports it | Model is ready; the UI is missing |

The pattern is worth stating plainly: **the data model is ahead of the UI on integrity and
behind the UI on career advice.** Everything the integrity engine produces has a home in the
schema and nowhere to render. Almost everything the dashboard displays has a place to render
and no source.

---

## Summary of decisions this audit forces

None of these are mine to make. Each changes scope.

1. Dashboard metrics: keep the approved composition, replace the six undefined scores with
   defined ones? (D1, C4)
2. Add a page-render overlay mode inside the approved evidence layout, or design a separate
   integrity screen? (D2, B2, B3)
3. Design the missing upload and auth screens in Stitch, or build them from the design system
   without a Stitch source? (B1, B7)
4. Cut Applications, Jobs browse and global search, or amend section 13? (C1, C2)
5. Keep the AI Assistant, and if so, in which phase and under what cost ceiling? (C3)
6. Move the skill-gap computation server-side, keeping the interaction as designed? (D6)
7. Relabel "Update Resume" and decide whether "For Recruiters" stays in the header. (D7, D8)
8. Reconcile the mobile bottom bar with the desktop sidebar. (D9)
