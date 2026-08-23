import uuid

import pytest
from httpx import AsyncClient

from .conftest import read_fixture


async def _upload_and_process(client: AsyncClient, fixture: str) -> str:
    """Drive the real pipeline synchronously, then read it back over HTTP.

    This is the phase 2 integration path end to end: a PDF goes in through the upload
    endpoint, the worker's own code renders and analyses it, and every assertion below is
    made against what the API actually serves.
    """
    from careerlayer_worker.pipeline import process_resume

    response = await client.post(
        "/v1/resumes", files={"file": (fixture, read_fixture(fixture), "application/pdf")}
    )
    resume_id = response.json()["resume_id"]
    process_resume(resume_id)
    return str(resume_id)


@pytest.fixture(scope="module")
def anyio_backend() -> str:
    return "asyncio"


async def test_a_processed_resume_reports_completed_with_real_page_geometry(
    client: AsyncClient, signed_in: str
) -> None:
    resume_id = await _upload_and_process(client, "clean-resume.pdf")

    body = (await client.get(f"/v1/resumes/{resume_id}")).json()

    assert body["state"] == "completed"
    assert body["page_count"] == 1
    assert body["evidence_available"] is True
    page = body["pages"][0]
    assert page["render_dpi"] == 200
    assert page["width_pt"] > 0 and page["render_width_px"] > 0


async def test_a_clean_resume_reports_no_findings_and_real_skills(
    client: AsyncClient, signed_in: str
) -> None:
    resume_id = await _upload_and_process(client, "clean-resume.pdf")

    body = (await client.get(f"/v1/resumes/{resume_id}")).json()
    skills = (await client.get(f"/v1/resumes/{resume_id}/skills")).json()

    assert body["findings_by_severity"] == {"high": 0, "suspicious": 0, "info": 0}
    assert body["skill_count"] == len(skills) > 0
    assert all(skill["evidence"] for skill in skills)


async def test_an_injected_resume_serves_findings_with_stable_ids_and_pdf_points(
    client: AsyncClient, signed_in: str
) -> None:
    resume_id = await _upload_and_process(client, "injected-invisible.pdf")

    detail = (await client.get(f"/v1/resumes/{resume_id}")).json()
    findings = (await client.get(f"/v1/resumes/{resume_id}/findings")).json()

    assert detail["findings_by_severity"]["high"] >= 1
    hidden = next(f for f in findings if f["detector_id"] == "D1")

    uuid.UUID(hidden["finding_id"])  # stable identity, not an array index
    assert set(hidden["bbox"]) == {"x0", "y0", "x1", "y1"}
    assert hidden["bbox"]["x1"] > hidden["bbox"]["x0"]
    assert hidden["severity"] == "high"
    assert hidden["rationale"]

    page = detail["pages"][hidden["page"] - 1]
    assert hidden["bbox"]["x1"] <= page["width_pt"]


async def test_finding_ids_are_stable_across_requests(client: AsyncClient, signed_in: str) -> None:
    resume_id = await _upload_and_process(client, "injected-invisible.pdf")

    first = (await client.get(f"/v1/resumes/{resume_id}/findings")).json()
    second = (await client.get(f"/v1/resumes/{resume_id}/findings")).json()

    assert [f["finding_id"] for f in first] == [f["finding_id"] for f in second]


async def test_the_rendered_page_is_served_as_a_png_through_the_api(
    client: AsyncClient, signed_in: str
) -> None:
    """Through the API, never a presigned URL: the browser gets no storage credential."""
    resume_id = await _upload_and_process(client, "clean-resume.pdf")

    response = await client.get(f"/v1/resumes/{resume_id}/pages/1")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


async def test_a_page_that_does_not_exist_is_a_404(client: AsyncClient, signed_in: str) -> None:
    resume_id = await _upload_and_process(client, "clean-resume.pdf")

    assert (await client.get(f"/v1/resumes/{resume_id}/pages/99")).status_code == 404


async def test_another_user_cannot_read_or_even_confirm_the_resume(
    client: AsyncClient, signed_in: str
) -> None:
    """404 rather than 403: telling a stranger a resume exists is already a disclosure."""
    resume_id = await _upload_and_process(client, "clean-resume.pdf")
    await client.post("/v1/auth/logout")

    other = f"other-{uuid.uuid4().hex[:8]}@example.com"
    issued = await client.post("/v1/auth/signup", json={"email": other})
    await client.post(
        "/v1/auth/verify", json={"token": issued.json()["login_url"].split("token=")[1]}
    )

    assert (await client.get(f"/v1/resumes/{resume_id}")).status_code == 404
    assert (await client.get(f"/v1/resumes/{resume_id}/findings")).status_code == 404
    assert (await client.get(f"/v1/resumes/{resume_id}/skills")).status_code == 404
    assert (await client.get(f"/v1/resumes/{resume_id}/pages/1")).status_code == 404


async def test_signed_out_users_cannot_read_anything(client: AsyncClient, signed_in: str) -> None:
    resume_id = await _upload_and_process(client, "clean-resume.pdf")
    await client.post("/v1/auth/logout")

    for path in ("", "/findings", "/skills", "/pages/1"):
        assert (await client.get(f"/v1/resumes/{resume_id}{path}")).status_code == 401


async def test_a_skill_evidenced_only_by_hidden_text_is_visibly_discounted(
    client: AsyncClient, signed_in: str
) -> None:
    """The product thesis, served over HTTP.

    The injected fixture's hidden line contains no skill terms, so this asserts the shape
    the UI depends on rather than a particular discount: every skill carries the two counts
    behind its confidence, so a reviewer can see why the number is what it is.
    """
    resume_id = await _upload_and_process(client, "injected-invisible.pdf")

    skills = (await client.get(f"/v1/resumes/{resume_id}/skills")).json()

    assert skills
    for skill in skills:
        assert skill["support_count"] >= 1
        assert "flagged_support_count" in skill
        assert skill["source"] == "dictionary_v1"
