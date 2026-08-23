# CareerLayer

An auditable resume screening engine that can prove what it read, where it read it, and
whether anything in the document was trying to manipulate the reader.

A resume is written by the person being evaluated, who has a direct incentive to
manipulate the evaluator. CareerLayer treats every uploaded document as untrusted input:
it reads the document twice, once the way a machine does and once the way a human does,
reports the difference, and measures whether that difference changed the outcome.

This README is a stub. It gains an architecture diagram, the false positive rate, and the
measured cost per document in phase 5.

## Status

| Phase | Scope | State |
| --- | --- | --- |
| 0 | Repository skeleton, local stack, health endpoint | done |
| 1 | Integrity CLI: dual extraction, detectors D1-D6 | done |
| 2 | Upload, extract, document viewer | not started |
| 3 | Job matching with evidence-linked claims | not started |
| 4 | Impact canary, eval corpus, CI gate | not started |
| 5 | Observability, rate limits, deploy | not started |

## Running it locally

Requires Docker and GNU make. The integrity package additionally needs the `tesseract-ocr`
system package, which is not a Python dependency.

```
cp .env.example .env
make dev
curl localhost:8000/health/ready
```

`make dev` brings up Postgres with pgvector, Redis, MinIO, and the API. A ready response
means all three dependencies answered; a 503 names the one that did not.

| Target | Does |
| --- | --- |
| `make dev` | Build and start the stack |
| `make down` | Stop it |
| `make logs` | Follow the API log |
| `make test` | Both suites below |
| `make test-api` | API tests, inside the container |
| `make test-integrity` | Integrity package tests, on the host |
| `make lint` | ruff, ruff format, mypy |
| `make migrate` | Apply Alembic migrations |
| `make eval` | Phase 4 |

Host ports are read from `.env` because a development machine often already has Postgres
on 5432.

## The integrity CLI

The analysis engine runs with no server, no database and no web app:

```
pip install -e packages/integrity
python -m careerlayer.integrity resume.pdf
python -m careerlayer.integrity resume.pdf --json
```

See `packages/integrity/README.md` for the detector list and the thresholds.

## Safety constraints

These are product requirements, not aspirations.

1. **CareerLayer never auto-rejects a candidate.** Integrity findings are advisory and are
   always shown to a human. There is no bulk reject action, by design.
2. **A false flag is the expensive error.** A missed injection costs a company one wasted
   interview; a false flag costs a person a job. Thresholds are tuned in that direction,
   and the headline metric is the false positive rate on clean resumes.
3. **Every finding is explainable.** Exact text, page, location, and a plain-language
   reason. No opaque risk score.
4. **The adversarial corpus is synthetic and stays in this repository.** It is never
   tested against a real hiring pipeline.

Detection raises the cost of an attack. It does not eliminate it, and this system will not
claim otherwise.
