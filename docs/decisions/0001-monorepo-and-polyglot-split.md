# 0001. One repository, two languages, three services

Status: accepted
Date: 2026-08-22

## Context

CareerLayer needs span-level PDF introspection (bounding boxes, text render mode, fill
colour, character offsets) and OCR. PyMuPDF and Tesseract have no JavaScript equivalent
that preserves the span attributes the integrity engine is built on, so the analysis code
is Python and is not portable.

The document viewer overlays findings on page renders and wants server components and a
mature React ecosystem, so the UI is Next.js.

Rasterising and OCR-ing a multi-page PDF takes seconds to minutes. That cannot run inside
an HTTP request, so extraction needs a worker.

## Options considered

**One Next.js application, PDF work in a serverless function.** Rejected. Serverless
execution limits are shorter than a worst-case OCR pass, and the Python native
dependencies (MuPDF, Tesseract binaries) are awkward to ship into that runtime.

**One Python application serving server-rendered HTML.** Rejected. The document viewer is
the product's most interactive surface; building it in Jinja and htmx trades a week of UI
work for avoiding one HTTP contract.

**Separate repositories per service.** Rejected. Three repositories means three CI
configurations and a cross-repo dance for any change that touches the API contract, which
at this stage is most changes. The evaluation gate in section 11 also needs to run the
integrity package and the API together.

**One repository, Python analysis plus Next.js UI, three deployables.** Chosen.

## Decision

A single repository with `web/` (Next.js), `api/` (FastAPI), `worker/` (RQ), and
`packages/integrity/` (a pure Python library). The only contract between the JavaScript
and Python halves is the versioned HTTP API. Next.js never parses a PDF; Python never
renders UI.

`packages/integrity/` depends on nothing above it: no FastAPI import, no database import.
It takes a file path and returns findings, and it runs from a CLI with no server. This is
what makes the detectors testable in isolation and the eval suite cheap to run in CI.

## Consequences

- Two toolchains, two linters, two dependency managers. Accepted cost.
- The API and worker share Python code but are separate deployables, because their
  scaling shapes differ: the API is IO-bound and small, the worker is CPU-bound and large.
- A change to a response shape touches both halves in one commit, which is the point.
- The integrity package can be extracted into its own distribution later without
  untangling imports, because the dependency direction is enforced from day one.
