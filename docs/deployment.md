# Deploying CareerLayer to Render

This is a portfolio-grade deployment: a working, clickable instance on the free tier. It is
**not** the full production hardening in `execution-roadmap.md` (no rate/cost limits, no
email sign-in, no backups). What you get is the whole workflow running on real
infrastructure.

## Architecture on Render

| Piece | Render resource | Notes |
| --- | --- | --- |
| Postgres | Managed PostgreSQL (free) | Free plan is deleted after 30 days |
| Redis | Managed Key Value (free) | RQ job queue + sessions |
| API + worker | one Web Service (Docker, `worker/Dockerfile`) | uvicorn **and** the RQ worker in one container |
| Web | Web Service (Docker, `web/Dockerfile`) | Next.js, the only public entry point |
| Object storage | **not on Render** | bring an S3-compatible bucket (see below) |

Render has no free *background worker* plan, so the API service runs on the worker image
(it carries Tesseract and every package) and starts the RQ worker next to uvicorn. This
keeps the whole stack at **$0/month**. Trade-off: a free web service sleeps after ~15 min
idle, so resume/JD processing only runs while someone is using the app — fine for a demo,
and jobs queued while asleep run when it wakes.

To run the worker as its own always-on service instead, add a `type: worker` service on
`plan: starter` (~$7/mo) using `./worker/Dockerfile` and remove the
`python -m careerlayer_worker.main &` fragment from the API `dockerCommand` in `render.yaml`.

Everything is wired by [`render.yaml`](../render.yaml) except the five `S3_*` values and the
web service's `API_ORIGIN`, which you set in the dashboard after the first deploy.

## 1. Object storage

Any S3-compatible store works — the code uses path-style addressing and v4 signing.
Two free, no-fuss options:

**Supabase Storage** (no payment method required)
1. [supabase.com](https://supabase.com) → new project (free).
2. **Storage** → new bucket `careerlayer-resumes`, keep it **private**.
3. **Project Settings → Storage → S3 Connection** → note the **endpoint** and **region**,
   then create an **access key** (ID + secret).

**Cloudflare R2** (10 GB free, but asks for a card on file)
1. Dashboard → **R2 Object Storage** → enable → **Create bucket** `careerlayer-resumes`.
2. **Manage R2 API Tokens → Create**, *Object Read & Write*, scoped to the bucket. Copy the
   Access Key ID, Secret Access Key, and the S3 endpoint
   `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`.

Values for step 3 (set on the **careerlayer-api** service):

| Env var | Supabase | Cloudflare R2 |
| --- | --- | --- |
| `S3_ENDPOINT_URL` | `https://<ref>.supabase.co/storage/v1/s3` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY` | access key ID | Access Key ID |
| `S3_SECRET_KEY` | secret | Secret Access Key |
| `S3_BUCKET` | `careerlayer-resumes` | `careerlayer-resumes` |
| `S3_REGION` | project region, e.g. `us-east-1` | `auto` |

## 2. Create the Blueprint

1. Render dashboard → **New → Blueprint**. If the repo is not listed, click **Configure
   account** under GitHub and grant access to `ai-resmue-analyser`, then connect it.
2. Give the Blueprint a name (e.g. `careerlayer`), branch `main`, path `render.yaml`.
3. Render shows four resources (db, redis, `careerlayer-api`, `careerlayer-web`) → **Apply**.
4. `careerlayer-api` will crash-loop until step 3 (no S3 config) and `careerlayer-web`
   until `API_ORIGIN` is set — expected.

## 3. Fill in the config

In the Render dashboard:

- **careerlayer-api → Environment** → set `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`,
  `S3_SECRET_KEY`, `S3_BUCKET`, `S3_REGION` from step 1.
`careerlayer-web` needs nothing: `web/next.config.mjs` defaults the `/v1` proxy target to
`https://careerlayer-api.onrender.com`. Set `API_ORIGIN` there only if the API service is
renamed.

Then **Manual Deploy → Deploy latest commit** on the API service.

> **Why the proxy target is a literal in the source and not a blueprint env var.** A Render
> *code* deploy rebuilds from the new commit but does not re-read `render.yaml`'s env vars —
> only a blueprint **sync** does. A service can therefore ship new code with `API_ORIGIN`
> still unset and proxy every `/v1` request to the compose hostname `api:8000`, which does
> not resolve on Render and surfaces as an opaque `500 Internal Server Error` on sign-in.
> A default that is correct for the deployment cannot drift that way. `next start` re-reads
> the config at boot, so `API_ORIGIN` still overrides it — which is how compose keeps
> pointing at `http://api:8000` locally.

## 4. Verify

```bash
curl https://careerlayer-api.onrender.com/health/ready
# {"status":"ready","checks":{"postgres":"ok","redis":"ok"},...}
```

Open the web URL, sign in (the magic link is shown on screen — see auth note), upload a PDF
resume, wait for processing, paste a job description, run a match.

Migrations (`alembic upgrade head`) run as the first step of the API container's start
command, so the schema is applied on every deploy; it is a fast no-op when nothing is
pending.

## Auth on this deployment

`ENVIRONMENT=development` is set on purpose so the sign-in link is returned in the API
response and the frontend displays it — there is no mail server, and real email delivery
(feature B5) is not built yet. `COOKIE_SECURE=true` keeps the session cookie `Secure` over
Render's HTTPS.

Trade-off: the sign-in link briefly appears in a response body. Acceptable for a demo with
synthetic data; do not put anything real behind it. To close this, implement
`api/careerlayer_api/email.py` (SMTP) and set `ENVIRONMENT=production`.

## Free-tier caveats

- Free web services **sleep after ~15 min idle**; the next request takes ~30–60 s and, for
  the API box, that is also when queued resume/JD jobs get processed.
- Free Postgres is **deleted after 30 days** — upgrade to keep the data.
- The free instance has 512 MB RAM. A very large PDF (many pages, heavy OCR) can OOM the
  worker; the job is marked failed and is safe to re-run. Split the worker onto `starter`
  if this happens often.

## LLM (optional)

The blueprint sets `LLM_DATA_PROCESSING_MODE=disabled`, so requirement extraction and
matching run without a provider and return a structured `llm_disabled` result. To enable
real matching, set `LLM_API_KEY` and `LLM_DATA_PROCESSING_MODE=fixtures_only` (or
`production`, which also needs `LLM_PRIVACY_ATTESTATION_ID` / `LLM_PRIVACY_VERIFIED_AT`) on
`careerlayer-api`.
