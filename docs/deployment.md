# Deploying CareerLayer to Render

This is a portfolio-grade deployment: a working, clickable instance. It is **not** the full
production hardening in `execution-roadmap.md` (no rate/cost limits, no email sign-in, no
backups). What you get is the whole workflow running on real infrastructure.

## Architecture on Render

| Piece | Render resource | Notes |
| --- | --- | --- |
| Postgres | Managed PostgreSQL | Free plan is deleted after 30 days |
| Redis | Managed Key Value | RQ job queue + sessions |
| API | Web Service (Docker, `api/Dockerfile`) | FastAPI / uvicorn |
| Worker | Background Worker (Docker, `worker/Dockerfile`) | OCR + page rendering + LLM calls |
| Web | Web Service (Docker, `web/Dockerfile`) | Next.js, the only public entry point |
| Object storage | **not on Render** | bring an S3-compatible bucket (see below) |

Everything is wired by [`render.yaml`](../render.yaml) except the four `S3_*` secrets and the
web service's `API_ORIGIN`, which you paste in after the first deploy.

## 1. Object storage (Cloudflare R2)

R2 is S3-compatible, has a 10 GB free tier, and charges nothing for egress — the best fit
for a small project. AWS S3 or Backblaze B2 work identically; only the endpoint and region
differ.

1. Cloudflare dashboard → **R2** → **Create bucket**, name it `careerlayer-resumes`.
2. **R2 → Manage R2 API Tokens → Create API token**, permission **Object Read & Write**,
   scoped to that bucket. Copy the **Access Key ID**, **Secret Access Key**, and the
   **S3 API endpoint** (`https://<ACCOUNT_ID>.r2.cloudflarestorage.com`).

Keep these four values for step 3:

| Env var | Value |
| --- | --- |
| `S3_ENDPOINT_URL` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY` | the Access Key ID |
| `S3_SECRET_KEY` | the Secret Access Key |
| `S3_BUCKET` | `careerlayer-resumes` |

(`S3_REGION` is already set to `auto` in the blueprint; for AWS set it to the bucket region.)

## 2. Create the Blueprint

1. Push this repo to GitHub (already done: `github.com/diansour-king/ai-resmue-analyser`).
2. Render dashboard → **New → Blueprint** → connect the repo. Render reads `render.yaml`
   and shows five resources to create. Approve.
3. The first build of `careerlayer-api` and `careerlayer-worker` will **fail or crash-loop**
   until the S3 secrets are set and the web service knows the API URL — expected, fixed next.

## 3. Fill in the secrets

In the Render dashboard:

- **careerlayer-api → Environment** → set `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`,
  `S3_SECRET_KEY`, `S3_BUCKET` from step 1.
- **careerlayer-worker → Environment** → set the same four.
- **careerlayer-web → Environment** → set `API_ORIGIN` to the API service's URL, which
  Render shows on the API service page, e.g. `https://careerlayer-api.onrender.com`.

Then **Manual Deploy → Deploy latest commit** on api, worker, and web.

## 4. Verify

```
curl https://careerlayer-api.onrender.com/health/ready
# {"status":"ready","checks":{"postgres":"ok","redis":"ok"},...}
```

Open the web URL, sign in (the magic link is shown on screen — see auth note below), upload
a PDF resume, wait for the worker to finish, paste a job description, run a match.

Database migrations run automatically before each API deploy via the blueprint's
`preDeployCommand` (`alembic upgrade head`).

## Auth on this deployment

`ENVIRONMENT=development` is set on purpose so the sign-in link is returned in the API
response and the frontend displays it — there is no mail server, and real email delivery
(feature B5) is not built yet. `COOKIE_SECURE=true` is also set, so the session cookie
still carries the `Secure` flag over Render's HTTPS.

Trade-off: the sign-in link briefly appears in an HTTP response. Acceptable for a demo with
synthetic data; do not put anything real behind it. To close this properly, implement
`api/careerlayer_api/email.py` (SMTP) and set `ENVIRONMENT=production`.

## Cost and free-tier caveats

- Free web services **spin down after 15 minutes idle**; the first request then takes
  ~30–60 s. The worker (`starter` plan) and Postgres do not spin down.
- Free Postgres is **removed after 30 days**. Upgrade it before then to keep your data.
- The worker is on `starter` (not free) because OCR and 200-DPI page rendering exceed the
  free instance's memory.

## LLM (optional)

The blueprint sets `LLM_DATA_PROCESSING_MODE=disabled`, so requirement extraction and
matching run without a provider and return a structured `llm_disabled` result. To enable
real matching, set `LLM_API_KEY` and `LLM_DATA_PROCESSING_MODE=fixtures_only` (or
`production`, which additionally needs `LLM_PRIVACY_ATTESTATION_ID` /
`LLM_PRIVACY_VERIFIED_AT`) on both `careerlayer-api` and `careerlayer-worker`.
