# design

The Google Stitch export, verbatim. This directory is a reference, not source: nothing here
is edited to fit the application, and nothing here is imported by the web app.

```
stitch_careerlayer_ai_intelligence.zip        the original archive as exported
stitch_careerlayer_ai_intelligence/
  careerlayer_1/DESIGN.md                     Cinematic Dark, the landing experience
  careerlayer_2/DESIGN.md                     Professional Light ocean, the application
  careerlayer_landing_page/                   code.html and screen.png per screen
  careerlayer_dashboard/
  careerlayer_evidence_analysis/
  careerlayer_skill_gap_analysis/
  careerlayer_ai_assistant/
```

Five screens exist. Twelve routes implied by the navigation have no design, and the
authentication, upload and integrity-findings screens are among them. What is present, what
is missing, and what contradicts the build specification are documented in
`docs/ui-inventory.md` and `docs/ui-spec-gap-analysis.md`.

The two design systems are both authoritative and must not be merged. The landing page is the
dark cinematic brand experience; the internal application is the light ocean experience.
Screens that have no Stitch source are built from `careerlayer_2`.
