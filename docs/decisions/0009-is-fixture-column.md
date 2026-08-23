# 0009. The is_fixture column as a mechanical privacy gate

Status: accepted
Date: 2026-08-23

## Context

CareerLayer's privacy architecture establishes strict launch gates: no real user document may be
transmitted to an external LLM provider without explicit, verified zero-retention terms (Gate 1).
During development and CI, the system runs in `fixtures_only` mode.

A mechanism is required to distinguish synthetic fixtures from real user uploads at LLM call time.

## Options Considered

1. **Infer from filename or path (e.g., `injected-*.pdf` or `/fixtures/`).** Rejected: brittle,
   unreliable for user-supplied filenames, and impossible to enforce once stored in the database.
2. **Infer from environment (e.g., `ENVIRONMENT=test`).** Rejected: dangerous; a developer testing
   locally with a real resume would leak data if environment checks treated all local uploads as
   fixtures.
3. **Explicit database column `is_fixture BOOLEAN NOT NULL DEFAULT false`.** Chosen.

## Decision

Add `is_fixture` (BOOLEAN, NOT NULL, DEFAULT false) to `resumes` and `job_descriptions`:

1. All standard user uploads through HTTP endpoints write `is_fixture = false` by default.
2. Only test harnesses and evaluation corpus loaders explicitly set `is_fixture = true`.
3. In `fixtures_only` mode, the LLM privacy guard inspects the database rows involved in the
   operation and rejects any request containing `is_fixture == False` with a `privacy_gate` error.

## Consequences

- Real user resumes cannot be sent to an LLM provider during development or CI even if an engineer
  attempts to upload one.
- The privacy gate is mechanical, deterministic, and enforced in code rather than by convention.
