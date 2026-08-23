# 0007. Claims cite many spans, with a single primary span for backward compatibility

Status: accepted
Date: 2026-08-23

## Context

Section 6 of the master specification defined `claims.evidence_span_id` as a single nullable
foreign key with the constraint `NOT NULL WHERE met = true`. However, the scoring formula in
Phase 3 (section 2.3) includes corroboration as an input to evidence quality (`q`):

```
corroboration = min(1.0, 0.8 + 0.1 * (distinct_evidence_spans - 1))
```

A single foreign key cannot express that two or three separate lines across a resume corroborate
a requirement. Without many-to-many evidence citations, a requirement mentioned once and a
requirement demonstrated across three separate jobs would receive identical corroboration credit.

## Decision

1. `claims` maintains `primary_evidence_span_id` pointing to `text_spans.id` with the database check
   constraint `CHECK (met = false OR primary_evidence_span_id IS NOT NULL)`.
2. A join table `claim_evidence (claim_id, span_id)` carries the full set of cited evidence spans.
3. A join table `claim_findings (claim_id, finding_id)` carries the set of integrity findings that
   overlap the cited evidence spans and determine the claim's `integrity_factor`.

## Consequences

- The database mechanically enforces that a satisfied (`met = true`) claim cannot exist without
  grounding in at least one primary text span.
- Additional supporting text spans can be associated via `claim_evidence` to compute corroboration.
- Traceability and integrity discounting are preserved with full database relational integrity.
