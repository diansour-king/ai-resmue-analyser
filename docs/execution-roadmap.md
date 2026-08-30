# CareerLayer — Final Execution Roadmap

Produced 2026-08-28 by architect/release-manager review of the repository at
`D:\ai resmue analyser`, HEAD `d4d6425`. No code was modified to produce this document.

## How this document was verified

| Check | Method | Result |
| --- | --- | --- |
| Git history | `git log`, `git show --stat` | HEAD is `d4d6425 implement phase 3h gap analysis and skill projections` |
| Working tree | `git status` | Clean except a whitespace-only change to `.dockerignore` |
| Docs vs code | Read `docs/phase-3-architecture.md` §§6–14, `docs/ui-api-contract.md` §8 + endpoint summary, ADRs 0001–0009 | Compared route-by-route and file-by-file |
| Scoring + projection suites | **Executed** in an isolated Python 3.11 sandbox | **15 passed** (`test_scoring` 9, `test_projection` 4, `test_cli` 2) |
| API / worker / web suites | **Not executed** | See limitation below |

**Limitation, stated plainly.** The API, worker and web suites could not be run from this
session: the review sandbox has Python 3.10 (the project requires 3.11+ for `enum.StrEnum`),
no Docker, and `api/tests/conftest.py` needs real Postgres, Redis and MinIO. Every statement
below about those suites is derived from reading the code and the test names, not from a
green run. **Antigravity must run `make test` and `make lint` on Windows before trusting any
"complete" marking in this document.**

---

# STEP 1 — CURRENT PROJECT STATUS

## 1.1 Phase status — corrected against the repository

| Phase | Documented | **Actual** | Evidence |
| --- | --- | --- | --- |
| 0 Skeleton, stack, health | done | **COMPLETE** | `infra/docker-compose.yml`, `health.py` (liveness + readiness with per-dependency probe) |
| 1 Integrity engine D1–D6 | done | **COMPLETE** | `packages/integrity/**`, 47 tests across 9 files |
| 2 Resume ingestion + evidence | done | **COMPLETE** | `pdf_intake.py`, `worker/pipeline.py`, `routes/resumes.py`, `PageCanvas` + evidence UI |
| 3A Matching data model | COMPLETE | **COMPLETE** | `models/{job,match,audit}.py`, migration `111f6ef2e07c`, 26 model tests |
| 3B JD ingestion | COMPLETE | **COMPLETE** | `jd_intake.py`, `routes/jobs.py`, `worker/jd_pipeline.py` |
| 3C Structured LLM extraction | COMPLETE | **COMPLETE IN CODE, ACCEPTANCE NOT MET** | `llm/{client,guard,schemas,prompts,pricing}.py` all present; but §7.5 still contains **estimates**, and 3C's stated acceptance is that the table is replaced with token-counted measurements. **Gate 2 is open.** |
| 3D Claims and evidence matching | COMPLETE | **COMPLETE IN CODE, TEST GROUP INCOMPLETE** | `worker/matching.py` (549 lines) with citation validation, integrity-aware claims, idempotent retry. Missing three required injection tests — see 1.2 |
| 3E Deterministic scoring | COMPLETE | **COMPLETE — VERIFIED GREEN** | `packages/scoring/{engine,models,cli}.py`; 9 tests executed and passing in this review |
| 3F Match API + SSE | COMPLETE | **PARTIAL** | All four endpoints present and correct; **rate and cost limiting, which 3F's own test list requires, is entirely absent** |
| 3G Match results + evidence UI | COMPLETE | **COMPLETE** | `app/matches/**`, `RequirementTable`, `ScoreCard`, `ClaimDetail`, `MatchList`; 15 + 8 frontend tests |
| 3H Gap analysis + projections | "being implemented" | **COMPLETE AND COMMITTED** | Commit `d4d6425`: `projection.py` (297 lines), `GET /v1/matches/{id}/gaps`, `GapList.tsx`, `gaps/page.tsx`. The required property test `test_projections_match_full_hypothetical_rescore` exists and **passes**. The gaps page reads `projected_score` from the server; no client-side additive arithmetic remains |
| 3I Evaluation infrastructure | — | **NOT STARTED** | `eval/` contains only `README.md`; `make eval` prints a message and `exit 1` |
| 3J Security and cost hardening | — | **NOT STARTED** | No limiter, no budget accounting, no `/metrics`, no D7 detector |
| 3K End-to-end verification | — | **NOT STARTED** | No integration suite |
| Deployment / production packaging | — | **NOT STARTED, AND CURRENTLY BROKEN** | See 1.3 blockers B1–B4 |

**Your phase list was one checkpoint behind: 3H is done. It was also one checkpoint
optimistic: 3C and 3F have unmet acceptance criteria.**

## 1.2 Broken or incomplete inside phases marked complete

1. **Prompt-injection test group (3D).** Only `test_prompt_injection_nonce_delimiter` exists
   (in `test_phase3c_llm.py` and `test_phase3d_llm.py`). §14's 3D acceptance requires three
   more: the injected fixture producing claims **identical claim-by-claim** to the clean
   fixture, the delimiter-escape attempt, and an injected *job description*. The seven
   controls in §6 are implemented in code; two of them are not proven by test.
2. **Gate 2 (3C).** `docs/phase-3-architecture.md` §7.5 still reads "these are estimates".
   No token-counting measurement, no date stamp, no prompt-version stamp.
3. **Cost and rate limits (3F/§7.2).** Not one of the eight limits in §7.2 is enforced.
   There is no 429 path and no `cost_ceiling_reached` path anywhere in the API.
4. **SSE implementation quality.** `GET /v1/matches/{id}/events` polls the database every
   0.5 s per open connection, opening a fresh session each tick, capped at 600 iterations
   (5 minutes). Correct, and the stage sequence emits no percentage as specified — but it is
   a database query per connection per half-second, and a match that runs longer than five
   minutes silently ends the stream with no terminal event.
5. **`GET /v1/resumes/{id}/document`** from the UI contract is not implemented. The evidence
   screen works without it; confirm before treating it as a gap.
6. **Audit log** is written on `match_run_created` only. §12.3 asks for a record of every
   match run, by whom, over which documents — the JD ingestion and upload paths write none.

## 1.3 Production blockers — the ones that are not on any phase list

These were found by reading the build files, not by reading the phase plan. **B1 and B2 mean
the Docker stack has been unbuildable since Phase 3F merged.**

| # | Blocker | Evidence | Effect |
| --- | --- | --- | --- |
| **B1** | **API image cannot start.** `api/careerlayer_api/routes/matches.py:15` does `from careerlayer.scoring import ...`. `api/pyproject.toml` does **not** list `careerlayer-scoring`. `api/Dockerfile` never `COPY`s `packages/scoring`. `infra/docker-compose.yml` mounts only `../api:/srv/api` | `main.py` imports the matches router at module level, so the **entire API** fails at import. `make dev` is broken |
| **B2** | **Worker image cannot build.** `worker/pyproject.toml` requires `careerlayer-scoring`; `worker/Dockerfile` copies only `packages/integrity`, `api`, `worker` | `pip install -e /srv/worker` tries to resolve `careerlayer-scoring` from PyPI and fails the build |
| **B3** | **`httpx` is runtime-required, declared dev-only.** `llm/client.py` imports `httpx` inside `_call_anthropic_structured`; `api/pyproject.toml` lists httpx under `[project.optional-dependencies] dev` | Every provider call fails with `ModuleNotFoundError` in a non-dev image |
| **B4** | **No LLM environment plumbing.** `.env.example` contains zero `LLM_*` variables; compose passes none to `api` or `worker` | A deployed stack runs in `disabled` mode with no way to configure it short of editing compose |
| **B5** | **Sign-in cannot work in production.** No email sending exists. `settings.expose_login_links` is `environment == "development"`, and the session cookie sets `secure=not settings.expose_login_links` | `ENVIRONMENT=production` ⇒ nobody can log in. `ENVIRONMENT=development` ⇒ login links returned in HTTP responses **and** the session cookie loses its `Secure` flag. Both options are unshippable |
| **B6** | Compose is a development stack only | Bind mounts, `uvicorn --reload`, `npx next start`, MinIO with committed default credentials, no production compose or override, and the `pgvector/pgvector:pg16` image despite ADR 0008 |
| **B7** | No security-header middleware, no `/metrics` | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP all absent. §7.6 promises `/metrics`; nothing serves it |
| **B8** | No dependency pinning | Every Python dependency is a `>=` range with no lock file. `web/package-lock.json` exists; nothing equivalent on the Python side |
| **B9** | `README.md` status table says Phase 3 "not started" | Stale by eight checkpoints |
| **B10** | No error tracking, no log shipping, no backup story | `observability.py` renders JSON to stdout and nothing collects it |

**Not blockers, recorded so nobody re-litigates them:**
CORS is correctly unnecessary — `web/next.config.mjs` proxies `/v1/*` server-side, so the
browser is always same-origin and the session cookie never crosses an origin. CSRF exposure is
low for the same reason plus `SameSite=Lax` and JSON-only bodies, but the login/verify POSTs
deserve one explicit look during the security audit.

## 1.4 Missing UI / API / backend / worker / tests / deployment — summary

- **Missing UI:** limit-reached and gate-disabled states (`llm_disabled`, 429, `cost_ceiling_reached`);
  a stale-run badge when prompt/scoring versions differ; settings, profile, help (all deliberately post-MVP).
- **Missing API:** rate/cost limiting, `/metrics`, `GET /v1/resumes/{id}/document`, `/v1/overview`
  (the Overview screen derives its tiles from `listResumes`, which is acceptable), assistant endpoints (post-MVP).
- **Missing backend:** email delivery; global spend kill switch; audit writes on non-match actions.
- **Missing worker:** nothing structural. `matching.py` already handles privacy-gate, LLM and
  generic failures, sets `failure_code`, and clears claims for idempotent retry. RQ retry policy
  is not configured — a crashed job stays failed rather than retrying.
- **Missing tests:** the three injection tests, the whole cost-limit group (including under
  concurrency), a log-capture test asserting no secret and no document text is logged, the 3K
  end-to-end test, and any test that would have caught B1.
- **Missing deployment:** everything. There is no production image, no production compose, no
  migration-on-deploy step, no backup, no host, no CI.

## 1.5 Architecture debt worth naming

- `packages/scoring` is a shared dependency of both the API and the worker, but the build
  files treat it as if only the worker needs it. This is the root cause of B1/B2.
- SSE by database polling (see 1.2 #4) will not survive many concurrent users; Redis pub/sub
  is the eventual answer, not an MVP one.
- The API image and the worker image both `pip install -e` with `--reload` semantics baked in;
  there is no production build stage, only the note in `api/Dockerfile` that "Phase 5 builds
  the production image from a separate stage".
- §14's dependency chain places 3I before 3J. There is **no code dependency** between them —
  see Step 4, where I recommend re-ordering.

---

# STEP 2 — DOCUMENTED REQUIREMENT vs ACTUAL IMPLEMENTATION

| Capability | Documented | Implemented | Verdict |
| --- | --- | --- | --- |
| Authentication | §UI-contract 1, ADR 0005 passwordless | `routes/auth.py`: signup, login (uniform response for unknown addresses), verify, logout, `/me`, onboarding; hashed tokens; HttpOnly SameSite=Lax cookie | **Code complete. Undeliverable without email (B5)** |
| Resume upload | Validate by parsing, 20 MB / 40 page caps | `pdf_intake.py` + `routes/resumes.py`, caps in `settings.py`, 10 upload tests | **Complete** |
| Resume processing | Extract → render 200 DPI → OCR → D1–D6 → persist | `worker/pipeline.py`, 11 tests | **Complete** |
| Integrity analysis | D1–D6 | Six detectors, 31 detector tests | **Complete.** D7/D8 not built (§6, correctly deferred) |
| JD ingestion | Paste + PDF, NFKC, offset stability, zero LLM calls | `jd_intake.py`, `worker/jd_pipeline.py`, 3+7 tests | **Complete** |
| Requirement extraction | Structured output, provenance validated, `llm_calls` on every attempt | `llm/client.py` (647 lines), `worker/requirement_extraction.py` | **Complete in code; Gate 2 open** |
| Matching | One call, nonce delimiters, citations validated against an enumerated set | `worker/matching.py` | **Complete in code; injection test group incomplete** |
| Deterministic scoring | Standalone package, no FastAPI, no SQLAlchemy, CLI over a JSON dump | `packages/scoring` — imports neither; CLI present | **Complete — executed and green in this review** |
| Evidence viewer | Rendered page, bbox overlay, PDF points | `PageCanvas`, `coordinates.ts`, evidence routes | **Complete** |
| Match API | POST/GET/list + SSE, idempotent re-match | All four; dedup returns `reused: true` without re-queuing | **Complete except limits** |
| SSE | Stage sequence, no percentage | `queued → scoring → canary → complete/failed`, keep-alives | **Complete; polling implementation is debt** |
| Skill gap analysis | Server-side projections, three categories, no market-demand caption | `projection.py` + `GapList.tsx`; `classify_gap_category` implements unverifiable/partial/missing | **Complete and verified** |
| AI assistant | Unscoped in the contract | Absent | **Correctly absent** |
| Dashboard | Row counts only, no composite scores | `app/page.tsx` — three tiles, all row counts, comment explains why | **Complete and specification-faithful** |
| Settings / profile / help | Out of scope (§8) | Absent | **Correctly absent** |
| Deployment | Phase 5 | Absent + broken build files | **Blocker** |
| Environment config | `.env.example` documents everything | No `LLM_*` at all | **Blocker (B4)** |
| Production security | §12 privacy gate, §7.2 limits | Privacy gate complete and correct in all three modes; limits absent | **Half done** |
| Observability | Structured logs + `/metrics` | structlog with an explicit "identifiers, never content" contract; no `/metrics`, no collector | **Half done** |
| Error handling | One envelope everywhere | `main.py` handlers wrap everything into `{error:{code,message},request_id}`; unhandled exceptions leak nothing but a request id; `ApiError` mirrors it in the frontend | **Complete and genuinely good** |

---

# STEP 3 — SCOPE

## A. PRODUCTION MVP — the only things that may be worked on

The core workflow, end to end, deployed:

> sign in → upload resume → integrity analysis → paste or upload a JD → requirement
> extraction → match → deterministic score → requirement-level evidence → integrity
> warnings → skill gaps → explainable results

Everything already built serves that path. What is still **required** for MVP:

1. Repair the build so the stack runs (B1–B4).
2. Real sign-in — email delivery, and a cookie policy independent of `ENVIRONMENT` (B5).
3. Enforce §7.2 limits and the global kill switch — an LLM endpoint without a spend ceiling
   is not shippable at any quality bar.
4. Close Gate 2 (measured cost) and finish the injection test group.
5. One end-to-end test on the real stack (3K).
6. Production packaging and deploy (new phase 3L).
7. README truthful, quoting **no** accuracy number.

## B. POST-MVP — explicitly deferred, with the decision recorded

| Feature | Decision | Reason |
| --- | --- | --- |
| **AI Assistant** | **CUT from MVP.** Do not build | `ui-api-contract.md` §8 lists it as unscoped; gap analysis C3 says "not forbidden, but entirely unscoped". An unscoped LLM surface is also an unbounded cost surface |
| **Applications** | **CUT permanently** | §13 non-goal, gap analysis C1. Not an ATS |
| **Job search / browse** | **CUT permanently** | §13 non-goal, gap analysis C2. No scraping, no integrations |
| **Recruiter functionality** | **CUT permanently** | Gap analysis D8. Product principle 1 — CareerLayer never auto-rejects |
| **Profile / settings / help** | **DEFER** | §8: unspecified, low risk, unscoped. Sign-out already exists in `AppShell` |
| **Advanced analytics / composite scores** | **CUT permanently** | Gap analysis D1/C4 and §10 forbid undefined composite numbers. The Overview's row-count tiles are the correct answer |
| **Embeddings / vector search** | **CUT from Phase 3** | ADR 0008. Note: compose still pulls the `pgvector` image — remove it during 3L |
| **Market-demand data** | **CUT permanently** | Gap analysis C5 — no data source exists in the specification or the stack |
| **Phase 3I evaluation infrastructure** | **DEFER to post-MVP** | See the re-sequencing argument in Step 4. It gates *claiming accuracy numbers*, not shipping the product |
| **D7 / D8 detectors** | **DEFER** | §6 D7 tier 3 spends an LLM call per uncertain span. New cost surface, no MVP need |
| **Resume versioning, notifications** | **DEFER** | Gap analysis C7, C6. No table, no phase |
| **SSE via Redis pub/sub** | **DEFER** | Polling works at MVP concurrency |

**Scope discipline rule for Antigravity: if a task is not in list A, it does not get written,
even if a Stitch screen shows it.**

---

# STEP 4 — REMAINING PHASES

## 4.1 Recommended re-sequencing — read this before executing

Three deviations from `phase-3-architecture.md` §14, each justified:

1. **3I moves after launch.** §14 chains `3H → 3I → 3J → 3K`. There is no code dependency
   from 3J or 3K on 3I: the eval harness reads files in git and touches no application code.
   §11.7 and checklist item 13 require only that the README quotes no accuracy number, which
   costs one edit. Building a 250-item labelled corpus (§13 items 5–7, ~15–20 hours of two
   people's attention) before deploying a working product is the single largest avoidable
   delay in the plan. **Ship, then measure, then claim.**
2. **3F's cost-limit tests are absorbed into 3J.** They were never written under 3F, and the
   limiter they test lives in 3J. Keeping them nominally under 3F only makes 3F look complete
   when it is not.
3. **A new phase 3L — Deployment packaging is added.** §14 has no deployment checkpoint;
   `api/Dockerfile` defers it to "Phase 5". Blockers B1–B4 and B6 make it mandatory, and it is
   the last thing standing between a green test suite and a running product.

## 4.2 Phase table

### CP-1 — Build repair and dependency correctness *(new; unblocks everything)*

- **Objective.** `make dev` builds and starts, and every service imports what it uses.
- **Files.** `api/pyproject.toml` (add `careerlayer-scoring`, move `httpx` to runtime),
  `api/Dockerfile` (COPY `packages/scoring` + `packages/integrity`, install them),
  `worker/Dockerfile` (COPY `packages/scoring`, install it),
  `infra/docker-compose.yml` (mount `../packages` for api and worker; pass `LLM_*`),
  `.env.example` (every `LLM_*` variable from `settings.py`, defaulting to `disabled`),
  `Makefile` (a `make smoke` target).
- **Tests.** `api/tests/test_health.py` gains an import-surface test asserting
  `careerlayer.scoring` and `httpx` import inside the API process. Manual: `make dev`
  followed by `curl localhost:8000/health/ready` returning `{"status":"ready"}`.
- **Acceptance.** Full stack up from a clean `docker system prune`; API and worker both
  healthy; `/v1/matches` reachable; a fresh clone with no `.env` edits makes **zero** provider
  calls and says `llm_disabled` clearly.
- **Docker.** Required. **Provider.** No.

### CP-2 — Authentication completion

- **Objective.** A stranger can sign in on a deployed instance.
- **Files.** `api/careerlayer_api/email.py` (new), `settings.py`
  (`smtp_host/port/user/password/from_address`, and a new `cookie_secure: bool` that is
  **not** derived from `environment`), `routes/auth.py` (send instead of returning the link),
  `infra/docker-compose.yml` (optional Mailhog for local development), `.env.example`.
- **Tests.** `test_auth.py`: the link is sent, not returned, when
  `ENVIRONMENT != development`; the cookie carries `Secure`, `HttpOnly`, `SameSite=Lax` when
  `cookie_secure=true`; a send failure degrades to a logged error and still returns 202
  (no account enumeration); token single-use and expiry unchanged.
- **Acceptance.** With `ENVIRONMENT=production` and SMTP configured, a real address receives a
  working link; no response body ever contains a token.
- **Docker.** Optional (Mailhog). **Provider.** SMTP required for the live check.

### CP-3 — Phase 3J-core: security and cost hardening

- **Objective.** Every §7.2 limit is code, and the gates are enforced rather than intended.
- **Files.** `api/careerlayer_api/limits.py` (new — Redis fixed-window counters),
  `routes/matches.py` + `routes/jobs.py` (apply limits, return 429 with `Retry-After` and 403
  `daily_limit_reached` / `cost_ceiling_reached`), `llm/guard.py` (global spend kill switch
  flipping to `disabled`), `observability.py` + a new `/metrics` route (calls, tokens, spend by
  purpose/model/prompt version, all derived from `llm_calls`), audit writes in `routes/jobs.py`
  and `routes/resumes.py`, `main.py` (security-header middleware),
  `web/src/lib/api.ts` + `AsyncState` (limit-reached and gate-disabled states).
- **Tests.** New `api/tests/test_limits.py`: 10/hour, 50/day, 20 JDs/day, $2.00/day, global
  $50 kill switch; **each enforced correctly under concurrency**; failed and refused attempts
  counted toward the ceiling. New `api/tests/test_logging.py`: a log-capture test asserting no
  API key and no document text appears in any emitted line. `test_phase3c_llm.py` extended for
  the guard in all three modes with a real (non-fixture) document refused in `fixtures_only`.
- **Acceptance.** Gate 3 closes. A user who exceeds a limit sees a specific message, not a 500.
- **Docker.** Required (Redis). **Provider.** No — mock the client.

### CP-4 — Gate 2 and the injection test group

- **Objective.** Cost is measured, not estimated; the two unproven injection controls are proven.
- **Files.** `docs/phase-3-architecture.md` §7.5 (replaced with measurements, stamped with date
  and prompt version), a small `scripts/measure_tokens.py`, `api/tests/test_phase3d_llm.py`,
  `worker/tests/test_matching.py`, plus injected/clean fixture pairs under
  `packages/integrity/tests/fixtures`.
- **Tests.** The injected fixture yields claims **identical claim-by-claim** to the clean
  fixture; the delimiter-escape attempt changes nothing; an injected *job description* changes
  no requirement; token counts recorded for both call types.
- **Acceptance.** §7.5 contains no estimate. Gate 2 closes. 3C and 3D acceptance both met.
- **Docker.** No. **Provider.** **Yes** — an Anthropic key, run in `fixtures_only`. This is the
  only checkpoint that requires the provider.

### CP-5 — Phase 3K: end-to-end production verification

- **Objective.** The whole thing, on real infrastructure, doing what the product exists to do.
- **Files.** `api/tests/test_e2e_phase3.py` (new), `Makefile` (`make test-e2e`), README.
- **Tests.** The single end-to-end test from §14: upload the injected fixture, ingest a JD whose
  requirements the hidden text is designed to satisfy, run a match, assert the score,
  `unmet_required_count`, `impact_delta`, the `unverifiable` gap category, and that the evidence
  responses carry the finding that caused it. Plus the full gate: every suite green, `ruff`,
  `ruff format --check`, `mypy --strict` on all three trees, ESLint, `tsc --noEmit`, and the
  Next.js production build.
- **Acceptance.** All of the above pass with the Docker stack up and the worker consuming.
  README states what Phase 3 does and quotes **no** accuracy number.
- **Docker.** Required. **Provider.** No (recorded fixtures).

### CP-6 — Phase 3L: deployment packaging *(new)*

- **Objective.** An image someone else can run.
- **Files.** `api/Dockerfile` and `worker/Dockerfile` (production stage: no `--reload`,
  non-root user, no editable installs), `infra/docker-compose.prod.yml` (no bind mounts, no
  default credentials, restart policies, healthchecks on api/web), a migration step on deploy,
  `docs/deployment.md`, `README.md` status table, `.env.production.example`,
  pinned Python dependencies (constraints file or `uv.lock`), remove the `pgvector` image per
  ADR 0008.
- **Tests.** Production images build from a clean context; the stack comes up from
  `docker-compose.prod.yml` alone; `alembic upgrade head` runs against a fresh database;
  `/health/ready` returns 200; a restore-from-backup rehearsal.
- **Acceptance.** A clean machine with Docker and a `.env` reaches a working sign-in page.
- **Docker.** Required. **Provider.** SMTP + Anthropic for a live instance.

### CP-7 — Final security audit

- **Objective.** Walk Step 5's must-have column and sign it off.
- **Files.** `docs/security-review.md` (new), whatever the walk turns up.
- **Tests.** `pip-audit` / `npm audit` clean of highs; a secret scan over history; a manual
  authorization sweep asserting every route filters by `user_id` (spot-checked as correct in
  this review — every match, job and resume query carries `== user.id`).
- **Acceptance.** Every must-have item ticked or explicitly waived in writing.
- **Docker.** No. **Provider.** No.

### POST-MVP — Phase 3I, then the deferred list

Unchanged from §14's 3I definition. Run it when you want to publish a number. Until it has
run on a sealed test split, **no accuracy claim may appear in the README, the UI, or anywhere
else** — that constraint is the whole reason 3I can safely wait.

---

# STEP 5 — PRODUCTION READINESS CHECKLIST

## MUST HAVE BEFORE DEPLOYMENT

| Area | Item | State | Checkpoint |
| --- | --- | --- | --- |
| Authentication | Passwordless flow, hashed tokens, single-use, expiry | **Done** | — |
| Authentication | Email delivery; login link never in a response body | **Missing (B5)** | CP-2 |
| Authentication | `Secure` cookie flag independent of `ENVIRONMENT` | **Broken (B5)** | CP-2 |
| Authorization | Every route filters by `user_id` | **Done** — verified by reading every query | CP-7 re-verify |
| Tenant isolation | Cross-user 404 rather than 403 on match/job/resume | **Done** | — |
| Secrets | No secret in git; `.env` gitignored | **Done** | — |
| Secrets | Production secrets from the platform, not a file | **Not established** | CP-6 |
| LLM privacy | Three-mode guard, fails closed, checked at call time | **Done and correct** | — |
| LLM privacy | Gate 1 attestation recorded before `production` mode | **Owner: Bikash** | Before CP-6 |
| Provider config | `LLM_*` in `.env.example` and compose | **Missing (B4)** | CP-1 |
| Rate limiting | 10/hour, 50/day match runs; 20 JDs/day | **Missing** | CP-3 |
| Cost ceiling | $2.00/user/day, $50 global kill switch, counting failed attempts | **Missing** | CP-3 |
| Upload validation | Validate by parsing before storing | **Done** | — |
| Malicious PDF | Parsed by PyMuPDF in the worker, not the API; render/OCR isolated; `ExtractionFailed` handled | **Done** | — |
| File size limits | 20 MB, 40 pages, 8,000 JD tokens | **Done** | — |
| Storage access | S3 credentials server-side only; browser never sees the API host | **Done** (`next.config.mjs` proxy) | — |
| DB migrations | Alembic chain, applies and rolls back | **Done**; not wired into deploy | CP-6 |
| Redis | Queue + readiness probe | **Done** | — |
| Worker reliability | Failure codes, idempotent claim clearing, safe retry | **Done** | — |
| Retries | RQ retry policy on transient failures | **Missing** | CP-3 |
| Idempotency | Match dedup on `(resume, jd, prompt_version, scoring_version)`; `reused: true` | **Done** | — |
| SSE | Stage sequence, no percentage, keep-alives, disconnect handling | **Done** | — |
| Error handling | One envelope; nothing internal crosses the boundary | **Done and good** | — |
| Logging | Structured, identifiers never content | **Done by convention** — no test enforces it | CP-3 |
| Health checks | `/health`, `/health/ready` with per-dependency naming | **Done** | — |
| Security headers | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy | **Missing (B7)** | CP-3 |
| CORS | Not required — same-origin BFF proxy | **N/A by design** | — |
| CSRF | `SameSite=Lax` + same-origin + JSON bodies | **Adequate**; confirm on auth POSTs | CP-7 |
| Dependency pinning | Python constraints/lock | **Missing (B8)** | CP-6 |
| Docker | Production stage, non-root, no `--reload`, no bind mounts | **Missing (B6)** | CP-6 |
| Docker | API and worker images actually contain `packages/scoring` | **BROKEN (B1, B2)** | **CP-1** |
| Deployment | Host, TLS, migration step, rollback | **Missing** | CP-6 |
| Backups | Postgres dump schedule + one restore rehearsal | **Missing** | CP-6 |
| Env vars | Complete, documented, safe defaults | **Partial (B4)** | CP-1, CP-6 |
| Frontend config | `API_ORIGIN` server-side only | **Done** | — |
| API config | Settings fail closed | **Done** | — |
| Truthfulness | README quotes no accuracy number; status table current | **Stale (B9)** | CP-5 |

## NICE TO HAVE AFTER DEPLOYMENT

- `/metrics` scraped by Prometheus; dashboards for spend, latency, `claims_rejected` (the
  route itself is CP-3; the collector is post-launch).
- Error tracking (Sentry) and shipped logs (B10).
- SSE over Redis pub/sub instead of polling.
- Phase 3I evaluation harness and the labelled corpus; only then, published accuracy numbers.
- D7/D8 detectors.
- CI pipeline running the full gate on every push.
- Per-user data export and deletion endpoints.
- CDN, image optimisation, `next/font`.
- Blue/green or rolling deploys.

---

# STEP 6 — EXECUTION PLAN

## Ownership model

- **Antigravity** — all code, tests, build files, migrations. It has the repository, the
  Windows toolchain, Docker, and it wrote everything up to `d4d6425`.
- **Claude** — specification and review: the exact diffs for the build repair, the limiter
  design, adversarial review of Antigravity's output, the §7.5 rewrite, the security audit
  document, README wording. **Claude writes no code into this repository.**
- **Bikash** — Gate 1 attestation, the Anthropic account and key, SMTP credentials, the
  deployment host, and the decision to deploy.

## Sequence

| # | Checkpoint | Owner | Docker | Provider | Blocks |
| --- | --- | --- | --- | --- | --- |
| 1 | **CP-1 Build repair** | Antigravity (spec from Claude) | **Yes** | No | Everything |
| 2 | **CP-2 Authentication completion** | Antigravity | Optional | SMTP | Launch |
| 3 | **CP-3 Phase 3J-core hardening** | Antigravity (limiter design from Claude) | **Yes** | No | Gate 3 |
| 4 | **CP-4 Gate 2 + injection tests** | Antigravity; Claude rewrites §7.5 | No | **Yes** | Gate 2, 3C/3D acceptance |
| 5 | **CP-5 Phase 3K end-to-end** | Antigravity | **Yes** | No | Launch |
| 6 | **CP-6 Phase 3L deployment** | Antigravity + Bikash | **Yes** | SMTP + Anthropic | Launch |
| 7 | **CP-7 Final security audit** | Claude reviews, Antigravity fixes | No | No | Launch |
| — | *Post-MVP:* 3I evaluation, then the deferred list | Antigravity + Bikash + 1 | No | No | Only accuracy claims |

CP-1 through CP-3 are strictly ordered. CP-4 can run in parallel with CP-3 once CP-1 lands,
if you have the key ready. CP-5 needs CP-2, CP-3 and CP-4 merged.

## Per-step detail

**CP-1 — files to touch, exactly:**

```
api/pyproject.toml            add "careerlayer-scoring" and "httpx>=0.28" to [project].dependencies
api/Dockerfile                COPY packages/scoring and packages/integrity; pip install -e both
                              before pip install -e "/srv/api[dev]"
worker/Dockerfile             COPY packages/scoring; pip install -e /srv/packages/scoring
                              before pip install -e /srv/worker
infra/docker-compose.yml      api.volumes += ../packages:/srv/packages
                              worker.volumes += ../packages/scoring:/srv/packages/scoring
                              api.environment and worker.environment += every LLM_* var
.env.example                  LLM_PROVIDER, LLM_MODEL, LLM_FALLBACK_MODEL, LLM_API_KEY,
                              LLM_BASE_URL, LLM_INFERENCE_GEO, LLM_TIMEOUT_SECONDS,
                              LLM_MAX_RETRIES, LLM_TEMPERATURE,
                              LLM_MAX_OUTPUT_TOKENS_EXTRACTION, LLM_MAX_OUTPUT_TOKENS_MATCHING,
                              LLM_CACHE_TTL, LLM_DATA_PROCESSING_MODE=disabled,
                              LLM_PRIVACY_ATTESTATION_ID, LLM_PRIVACY_VERIFIED_AT
api/tests/test_health.py      import-surface test (see below)
```

Acceptance for CP-1 is one command and one assertion:

```
make down && make dev && curl -s localhost:8000/health/ready
# {"status":"ready","checks":{"postgres":"ok","redis":"ok"},...}
docker compose -f infra/docker-compose.yml exec api python -c "import careerlayer.scoring, httpx; print('ok')"
```

**Notes carried into later steps**

- CP-3's limiter must count **attempts, not successes** — `llm_calls` is written on every
  attempt including failures and refusals, and §7.2 says a ceiling that only counts successes
  is not a ceiling. The concurrency test is the point of the checkpoint; a limiter that passes
  serially and fails under two simultaneous requests is the failure mode being tested for.
- CP-4 is the only step that spends money. Run it in `fixtures_only` with `is_fixture=true`
  documents; the guard will refuse anything else, which is the design working.
- CP-6 must delete the `pgvector` image from compose (ADR 0008) and must not carry the
  development MinIO credentials into production.

---

# FINAL PROJECT COMPLETION ROADMAP

**From `d4d6425` to "CareerLayer production MVP ready for deployment", shortest realistic path:**

```
CP-1  Build repair                    ── the API cannot start in Docker today; nothing
      (api/worker pyproject +            downstream can be verified until this lands
       Dockerfiles + compose + env)

CP-2  Authentication completion       ── email delivery; cookie Secure decoupled from
                                         ENVIRONMENT. Without it nobody can sign in

CP-3  Phase 3J-core hardening         ── §7.2 limits, kill switch, /metrics, audit writes,
                                         security headers, log-capture test. Closes Gate 3

CP-4  Gate 2 + injection test group   ── measured token costs replace §7.5; the three
      (parallel with CP-3 if keyed)      missing injection tests. Closes 3C and 3D acceptance

CP-5  Phase 3K end-to-end             ── the injected-fixture E2E on the real stack, plus
                                         the full lint/type/build gate

CP-6  Phase 3L deployment packaging   ── production images, prod compose, pinned deps,
                                         migrations on deploy, backups, README truthful

CP-7  Final security audit            ── walk the must-have column, sign it off

──────────── DEPLOY ────────────

POST-MVP  Phase 3I evaluation → labelled corpus → sealed test split → only then may any
          accuracy number be published anywhere
```

Seven checkpoints. Four of them (CP-1, CP-2, CP-4, CP-6) are small and mechanical; CP-3 is the
only substantial new engineering; CP-5 and CP-7 are verification. **Phases 3A–3H are done and
do not need to be revisited.**

## EXACT NEXT CHECKPOINT FOR ANTIGRAVITY

> ### CP-1 — Build repair and dependency correctness
>
> **Do this and nothing else.** `api/careerlayer_api/routes/matches.py` imports
> `careerlayer.scoring`, `main.py` imports that router at module level, and neither
> `api/pyproject.toml` nor `api/Dockerfile` nor `infra/docker-compose.yml` makes
> `packages/scoring` available to the API container. The worker image has the mirror image of
> the same defect. **The Docker stack has been unbuildable since Phase 3F merged**, which means
> every "verified" marking from 3F onward was verified outside Docker.
>
> Files: `api/pyproject.toml`, `api/Dockerfile`, `worker/Dockerfile`,
> `infra/docker-compose.yml`, `.env.example`, `api/tests/test_health.py`.
>
> Done when: `make down && make dev` builds clean from a pruned Docker, `/health/ready`
> returns `{"status":"ready"}`, `import careerlayer.scoring` succeeds **inside the API
> container**, a POST to `/v1/matches` returns a structured `llm_disabled` error rather than a
> 500, and the existing suites still pass.
>
> Suggested checkpoint message: `repair api and worker packaging for the scoring package`
