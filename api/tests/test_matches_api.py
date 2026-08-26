import json
import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from careerlayer_api.main import app
from careerlayer_api.models import (
    Claim,
    ClaimEvidence,
    Extraction,
    JobDescription,
    JobSource,
    JobState,
    MatchRun,
    MatchRunState,
    ProcessingState,
    Requirement,
    RequirementKind,
    RequirementNecessity,
    Resume,
    TextSpan,
    User,
)
from careerlayer_api.settings import get_settings


async def _create_test_environment(
    user_email: str,
    *,
    resume_state: ProcessingState = ProcessingState.COMPLETED,
    job_state: JobState = JobState.COMPLETED,
    has_requirements: bool = True,
    create_match_run: bool = False,
    match_run_state: MatchRunState = MatchRunState.COMPLETED,
) -> dict[str, uuid.UUID]:
    """Helper to set up resumes, jobs, requirements, and optional match runs in DB."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        user_res = await session.execute(select(User).where(User.email == user_email))
        user = user_res.scalar_one()

        resume_id = uuid.uuid4()
        resume = Resume(
            id=resume_id,
            user_id=user.id,
            filename="backend_resume.pdf",
            storage_key="test_key",
            sha256=f"sha-{uuid.uuid4().hex[:12]}",
            byte_size=10240,
            page_count=2,
            state=resume_state,
        )
        session.add(resume)
        await session.flush()

        extraction = Extraction(
            id=uuid.uuid4(),
            resume_id=resume.id,
            method="text_layer",
            page_count=2,
            duration_ms=150,
        )
        session.add(extraction)
        await session.flush()

        span1 = TextSpan(
            id=uuid.uuid4(),
            extraction_id=extraction.id,
            page=1,
            seqno=0,
            x0=72.0,
            y0=100.0,
            x1=400.0,
            y1=120.0,
            text="Senior Backend Engineer with 6 years Python and FastAPI experience",
            font="Helvetica",
            font_size=12.0,
            colour="#000000",
            render_mode=0,
            opacity=1.0,
            char_start=0,
            char_end=68,
        )
        session.add(span1)
        await session.flush()

        job_id = uuid.uuid4()
        job = JobDescription(
            id=job_id,
            user_id=user.id,
            title="Senior Backend Engineer",
            company="TechFlow Systems",
            location="Remote",
            source=JobSource.PASTED,
            raw_text="Job description text for Senior Backend Engineer",
            normalized_text="Job description text for Senior Backend Engineer",
            sha256=f"sha-job-{uuid.uuid4().hex[:12]}",
            state=job_state,
        )
        session.add(job)
        await session.flush()

        req_id = uuid.uuid4()
        if has_requirements:
            req = Requirement(
                id=req_id,
                job_description_id=job.id,
                ordinal=1,
                text="5+ years Python in production",
                kind=RequirementKind.HARD_SKILL,
                necessity=RequirementNecessity.REQUIRED,
                criticality=3,
                weight=Decimal("3.0000"),
                evidence_start=0,
                evidence_end=6,
                evidence_quote="Python",
            )
            session.add(req)
            await session.flush()

        match_run_id = uuid.uuid4()
        if create_match_run:
            from careerlayer_api.llm.prompts import (
                PROMPT_VERSION_RESUME_MATCHING_V1,
                SYSTEM_PROMPT_RESUME_MATCHING_V1,
                ensure_prompt_version_async,
            )

            pv = await ensure_prompt_version_async(
                session,
                name=PROMPT_VERSION_RESUME_MATCHING_V1,
                purpose="matching",
                template=SYSTEM_PROMPT_RESUME_MATCHING_V1,
                model="claude-sonnet-5",
            )

            match_run = MatchRun(
                id=match_run_id,
                user_id=user.id,
                resume_id=resume.id,
                job_description_id=job.id,
                state=match_run_state,
                model="claude-sonnet-5",
                prompt_version_id=pv.id,
                scoring_version="v1",
                score=Decimal("80.00") if match_run_state == MatchRunState.COMPLETED else None,
                score_if_trusted=Decimal("80.00")
                if match_run_state == MatchRunState.COMPLETED
                else None,
                impact_delta=Decimal("0.00")
                if match_run_state == MatchRunState.COMPLETED
                else None,
                requirement_count=1 if match_run_state == MatchRunState.COMPLETED else None,
                unmet_required_count=0 if match_run_state == MatchRunState.COMPLETED else None,
                cost_usd=Decimal("0.0150") if match_run_state == MatchRunState.COMPLETED else None,
                latency_ms=1200 if match_run_state == MatchRunState.COMPLETED else None,
                narrative="Candidate is a direct fit for Python backend role."
                if match_run_state == MatchRunState.COMPLETED
                else None,
                failure_code="schema_violation"
                if match_run_state == MatchRunState.FAILED
                else None,
            )
            session.add(match_run)
            await session.flush()

            if match_run_state == MatchRunState.COMPLETED:
                claim = Claim(
                    match_run_id=match_run.id,
                    requirement_id=req_id,
                    met=True,
                    match_type="direct",
                    satisfaction=Decimal("1.0000"),
                    corroboration=Decimal("0.8000"),
                    integrity_factor=Decimal("1.0000"),
                    evidence_quality=Decimal("0.8000"),
                    weight_applied=Decimal("3.0000"),
                    contribution=Decimal("2.4000"),
                    confidence=Decimal("0.9800"),
                    primary_evidence_span_id=span1.id,
                    rationale="Direct match on Python production experience.",
                )
                session.add(claim)
                await session.flush()

                ce = ClaimEvidence(claim_id=claim.id, span_id=span1.id)
                session.add(ce)

        await session.commit()
        await engine.dispose()

    return {
        "user_id": user.id,
        "resume_id": resume_id,
        "job_id": job_id,
        "req_id": req_id,
        "match_run_id": match_run_id,
        "span_id": span1.id,
    }


@pytest.mark.asyncio
async def test_post_matches_validation_and_enqueue(
    client: AsyncClient, signed_in: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued_runs: list[str] = []

    def mock_enqueue(match_run_id: str) -> str:
        enqueued_runs.append(match_run_id)
        return f"job-{match_run_id}"

    monkeypatch.setattr("careerlayer_api.routes.matches.enqueue_match_processing", mock_enqueue)

    ctx = await _create_test_environment(signed_in)

    # 1. Valid request creates match and enqueues worker
    res = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(ctx["resume_id"]),
            "job_description_id": str(ctx["job_id"]),
        },
    )
    assert res.status_code == 202
    data = res.json()
    assert "match_run_id" in data
    assert data["state"] == "queued"
    assert data["reused"] is False
    assert data["duplicate_of_existing"] is False
    assert len(enqueued_runs) == 1
    assert enqueued_runs[0] == data["match_run_id"]

    # 2. Idempotent duplicate request returns existing run
    res_dup = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(ctx["resume_id"]),
            "job_description_id": str(ctx["job_id"]),
        },
    )
    assert res_dup.status_code == 202
    dup_data = res_dup.json()
    assert dup_data["match_run_id"] == data["match_run_id"]
    assert dup_data["reused"] is True
    assert dup_data["duplicate_of_existing"] is True
    # Should NOT have enqueued again
    assert len(enqueued_runs) == 1


@pytest.mark.asyncio
async def test_post_matches_unauthenticated(client: AsyncClient) -> None:
    # Unauthenticated client (no cookie) rejected with 401
    res = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(uuid.uuid4()),
            "job_description_id": str(uuid.uuid4()),
        },
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "unauthenticated"


@pytest.mark.asyncio
async def test_post_matches_missing_or_cross_user_documents(
    client: AsyncClient, signed_in: str
) -> None:
    ctx = await _create_test_environment(signed_in)

    # Missing Resume -> 404
    res_missing_res = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(uuid.uuid4()),
            "job_description_id": str(ctx["job_id"]),
        },
    )
    assert res_missing_res.status_code == 404
    assert res_missing_res.json()["error"]["code"] == "resume_not_found"

    # Missing Job -> 404
    res_missing_job = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(ctx["resume_id"]),
            "job_description_id": str(uuid.uuid4()),
        },
    )
    assert res_missing_job.status_code == 404
    assert res_missing_job.json()["error"]["code"] == "job_not_found"

    # Cross-user resume attempt
    other_email = f"other-{uuid.uuid4().hex[:8]}@example.com"
    other_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    reg = await other_client.post("/v1/auth/signup", json={"email": other_email})
    tok = reg.json()["login_url"].split("token=")[1]
    await other_client.post("/v1/auth/verify", json={"token": tok})
    other_ctx = await _create_test_environment(other_email)

    # Current user tries to match using Other user's resume
    res_cross = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(other_ctx["resume_id"]),
            "job_description_id": str(ctx["job_id"]),
        },
    )
    assert res_cross.status_code == 404
    assert res_cross.json()["error"]["code"] == "resume_not_found"


@pytest.mark.asyncio
async def test_post_matches_not_ready_or_empty_requirements(
    client: AsyncClient, signed_in: str
) -> None:
    # 1. Resume still processing -> 422 resume_not_ready
    ctx_res_proc = await _create_test_environment(
        signed_in, resume_state=ProcessingState.PROCESSING
    )
    res1 = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(ctx_res_proc["resume_id"]),
            "job_description_id": str(ctx_res_proc["job_id"]),
        },
    )
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "resume_not_ready"

    # 2. Job description still processing -> 422 job_not_ready
    ctx_job_proc = await _create_test_environment(signed_in, job_state=JobState.PROCESSING)
    res2 = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(ctx_job_proc["resume_id"]),
            "job_description_id": str(ctx_job_proc["job_id"]),
        },
    )
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "job_not_ready"

    # 3. Job description with 0 requirements -> 422 job_has_no_requirements
    ctx_no_reqs = await _create_test_environment(signed_in, has_requirements=False)
    res3 = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(ctx_no_reqs["resume_id"]),
            "job_description_id": str(ctx_no_reqs["job_id"]),
        },
    )
    assert res3.status_code == 422
    assert res3.json()["error"]["code"] == "job_has_no_requirements"


@pytest.mark.asyncio
async def test_get_matches_list_and_ownership(client: AsyncClient, signed_in: str) -> None:
    ctx1 = await _create_test_environment(signed_in, create_match_run=True)
    ctx2 = await _create_test_environment(signed_in, create_match_run=True)

    # 1. Authenticated user sees own match runs
    res = await client.get("/v1/matches")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) >= 2
    match_ids = [item["match_run_id"] for item in data["items"]]
    assert str(ctx1["match_run_id"]) in match_ids
    assert str(ctx2["match_run_id"]) in match_ids

    # 2. Another user cannot see this user's matches
    other_email = f"other2-{uuid.uuid4().hex[:8]}@example.com"
    other_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    reg = await other_client.post("/v1/auth/signup", json={"email": other_email})
    tok = reg.json()["login_url"].split("token=")[1]
    await other_client.post("/v1/auth/verify", json={"token": tok})

    other_list = await other_client.get("/v1/matches")
    assert other_list.status_code == 200
    other_ids = [item["match_run_id"] for item in other_list.json()["items"]]
    assert str(ctx1["match_run_id"]) not in other_ids
    assert str(ctx2["match_run_id"]) not in other_ids


@pytest.mark.asyncio
async def test_get_match_detail_and_claims(client: AsyncClient, signed_in: str) -> None:
    ctx = await _create_test_environment(
        signed_in, create_match_run=True, match_run_state=MatchRunState.COMPLETED
    )

    # 1. Own completed match detail
    res = await client.get(f"/v1/matches/{ctx['match_run_id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["match_run_id"] == str(ctx["match_run_id"])
    assert data["state"] == "completed"
    assert data["score"] == 80.0
    assert data["score_if_trusted"] == 80.0
    assert data["impact_delta"] == 0.0
    assert data["unmet_required_count"] == 0
    assert data["requirement_count"] == 1
    assert data["job"]["title"] == "Senior Backend Engineer"
    assert len(data["claims"]) == 1
    claim = data["claims"][0]
    assert claim["met"] is True
    assert claim["match_type"] == "direct"
    assert claim["satisfaction"] == 1.0
    assert claim["evidence"]["span_id"] == str(ctx["span_id"])
    assert "Senior Backend Engineer" in claim["evidence"]["quote"]

    # Security check: No raw provider prompts or database credentials
    raw_str = json.dumps(data)
    assert "ANTHROPIC_API_KEY" not in raw_str
    assert "postgresql://" not in raw_str
    assert "system_prompt" not in raw_str

    # 2. Non-existent match -> 404
    res_none = await client.get(f"/v1/matches/{uuid.uuid4()}")
    assert res_none.status_code == 404
    assert res_none.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_match_events_sse(client: AsyncClient, signed_in: str) -> None:
    ctx = await _create_test_environment(
        signed_in, create_match_run=True, match_run_state=MatchRunState.COMPLETED
    )

    # 1. Completed match SSE stream emits complete event immediately
    res = await client.get(f"/v1/matches/{ctx['match_run_id']}/events")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    body = res.text
    assert "event: complete" in body
    assert f'"match_run_id": "{ctx["match_run_id"]}"' in body
    assert '"score": 80.0' in body

    # 2. Unauthorized access to SSE stream rejected with 404
    other_email = f"other3-{uuid.uuid4().hex[:8]}@example.com"
    other_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    reg = await other_client.post("/v1/auth/signup", json={"email": other_email})
    tok = reg.json()["login_url"].split("token=")[1]
    await other_client.post("/v1/auth/verify", json={"token": tok})

    res_unauth = await other_client.get(f"/v1/matches/{ctx['match_run_id']}/events")
    assert res_unauth.status_code == 404
    assert res_unauth.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_match_events_failed_and_canary(client: AsyncClient, signed_in: str) -> None:
    # 1. Failed match run emits failed event immediately
    ctx_failed = await _create_test_environment(
        signed_in, create_match_run=True, match_run_state=MatchRunState.FAILED
    )
    res_failed = await client.get(f"/v1/matches/{ctx_failed['match_run_id']}/events")
    assert res_failed.status_code == 200
    assert "event: failed" in res_failed.text
    assert '"failure_code": "schema_violation"' in res_failed.text

    # 2. Match run with impact delta > 0 emits canary event before complete
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        match_run_res = await session.execute(
            select(MatchRun).where(MatchRun.id == ctx_failed["match_run_id"])
        )
        mr = match_run_res.scalar_one()
        mr.state = MatchRunState.COMPLETED
        mr.score = Decimal("75.00")
        mr.score_if_trusted = Decimal("90.00")
        mr.impact_delta = Decimal("15.00")
        await session.commit()
    await engine.dispose()

    res_canary = await client.get(f"/v1/matches/{ctx_failed['match_run_id']}/events")
    assert res_canary.status_code == 200
    body = res_canary.text
    assert "event: canary" in body
    assert '"impact_delta": 15.0' in body
    assert "event: complete" in body


@pytest.mark.asyncio
async def test_matches_pagination_and_filters(client: AsyncClient, signed_in: str) -> None:
    ctx1 = await _create_test_environment(signed_in, create_match_run=True)
    ctx2 = await _create_test_environment(signed_in, create_match_run=True)

    # Filter by resume_id
    res_res = await client.get(f"/v1/matches?resume_id={ctx1['resume_id']}")
    assert res_res.status_code == 200
    items = res_res.json()["items"]
    assert all(item["resume_id"] == str(ctx1["resume_id"]) for item in items)

    # Filter by job_description_id
    res_job = await client.get(f"/v1/matches?job_description_id={ctx2['job_id']}")
    assert res_job.status_code == 200
    items_job = res_job.json()["items"]
    assert all(item["job_description_id"] == str(ctx2["job_id"]) for item in items_job)

    # Limit parameter
    res_lim = await client.get("/v1/matches?limit=1")
    assert res_lim.status_code == 200
    data_lim = res_lim.json()
    assert len(data_lim["items"]) == 1


@pytest.mark.asyncio
async def test_post_matches_retry_on_failed_state(
    client: AsyncClient, signed_in: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    enqueued: list[str] = []

    def mock_enqueue(match_run_id: str) -> str:
        enqueued.append(match_run_id)
        return f"job-{match_run_id}"

    monkeypatch.setattr("careerlayer_api.routes.matches.enqueue_match_processing", mock_enqueue)

    ctx = await _create_test_environment(
        signed_in, create_match_run=True, match_run_state=MatchRunState.FAILED
    )

    # Posting against an existing FAILED run should reset to queued and re-enqueue
    res = await client.post(
        "/v1/matches",
        json={
            "resume_id": str(ctx["resume_id"]),
            "job_description_id": str(ctx["job_id"]),
        },
    )
    assert res.status_code == 202
    data = res.json()
    assert data["match_run_id"] == str(ctx["match_run_id"])
    assert data["state"] == "queued"
    assert data["reused"] is True
    assert data["duplicate_of_existing"] is False
    assert len(enqueued) == 1
    assert enqueued[0] == str(ctx["match_run_id"])
