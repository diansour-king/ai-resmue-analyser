# 0008. No pgvector or embedding retrieval in Phase 3 matching

Status: accepted
Date: 2026-08-23

## Context

Section 4 of the master specification originally envisioned pgvector and embedding-based candidate
retrieval prior to LLM scoring. In that model, document chunks would be embedded and top-k spans
retrieved to form the prompt.

## Decision

Phase 3 uses direct, full-context extraction and matching without vector retrieval or chunking:

1. A resume's complete text-layer span table is roughly 3,000 tokens, and a job description is
   roughly 3,000 tokens. Both fit comfortably in a single call alongside system prompts and schemas
   under Claude Sonnet 5's context window.
2. Retrieval exists to choose what to omit; when everything fits with high fidelity, embedding
   retrieval introduces recall failure risks (omitting valid evidence) and indexing complexity with
   zero upside.
3. The `pgvector` PostgreSQL extension remains enabled from Phase 0 for future cross-document corpus
   search features (Phase 4+), but no embedding columns or retrieval pipelines are built in Phase 3.

## Revisit Trigger

If a single resume's span table plus job description exceeds 100,000 tokens, or if multi-resume
ranking against multiple JDs is introduced, retrieval becomes justified and this decision will be
reopened with empirical measurements.
