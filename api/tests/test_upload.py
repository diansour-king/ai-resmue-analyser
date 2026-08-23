import pytest
from httpx import AsyncClient

from .conftest import read_fixture


async def test_upload_requires_a_session(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/resumes",
        files={"file": ("resume.pdf", read_fixture("clean-resume.pdf"), "application/pdf")},
    )

    assert response.status_code == 401


async def test_a_valid_pdf_is_accepted_and_handed_to_the_worker(
    client: AsyncClient, signed_in: str, no_real_queue: list[str]
) -> None:
    response = await client.post(
        "/v1/resumes",
        files={"file": ("alex.pdf", read_fixture("clean-resume.pdf"), "application/pdf")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["state"] == "queued"
    assert body["page_count"] == 1
    assert no_real_queue == [body["resume_id"]]


async def test_the_request_does_not_do_the_work(
    client: AsyncClient, signed_in: str, no_real_queue: list[str]
) -> None:
    """Upload must hand off, not process.

    Rendering and OCR take seconds to minutes. If this ever returns "completed" the pipeline
    has moved into the request and the API will start timing out on long documents.
    """
    response = await client.post(
        "/v1/resumes",
        files={"file": ("alex.pdf", read_fixture("clean-resume.pdf"), "application/pdf")},
    )

    assert response.json()["state"] == "queued"
    detail = await client.get(f"/v1/resumes/{response.json()['resume_id']}")
    assert detail.json()["findings_by_severity"] == {"high": 0, "suspicious": 0, "info": 0}


async def test_a_file_that_is_not_a_pdf_is_refused(
    client: AsyncClient, signed_in: str, no_real_queue: list[str]
) -> None:
    """Refused by parsing it, not by trusting the name or the content type it claims."""
    response = await client.post(
        "/v1/resumes",
        files={"file": ("resume.pdf", b"MZ\x90\x00 this is an executable", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_pdf"
    assert no_real_queue == []


async def test_an_empty_file_is_refused(
    client: AsyncClient, signed_in: str, no_real_queue: list[str]
) -> None:
    response = await client.post(
        "/v1/resumes", files={"file": ("resume.pdf", b"", "application/pdf")}
    )

    assert response.status_code == 422
    assert no_real_queue == []


async def test_an_oversize_file_is_refused_before_it_is_stored(
    client: AsyncClient,
    signed_in: str,
    monkeypatch: pytest.MonkeyPatch,
    no_real_queue: list[str],
) -> None:
    from careerlayer_api.settings import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "max_upload_bytes", 1024)

    response = await client.post(
        "/v1/resumes",
        files={"file": ("alex.pdf", read_fixture("clean-resume.pdf"), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "file_too_large"
    assert no_real_queue == []


async def test_a_document_over_the_page_cap_is_refused(
    client: AsyncClient,
    signed_in: str,
    monkeypatch: pytest.MonkeyPatch,
    no_real_queue: list[str],
) -> None:
    from careerlayer_api.settings import get_settings

    monkeypatch.setattr(get_settings(), "max_page_count", 1)

    response = await client.post(
        "/v1/resumes",
        files={"file": ("alex.pdf", read_fixture("clean-two-page.pdf"), "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "page_limit_exceeded"


async def test_reuploading_the_same_bytes_reuses_the_analysis(
    client: AsyncClient, signed_in: str, no_real_queue: list[str]
) -> None:
    content = read_fixture("clean-resume.pdf")
    first = await client.post("/v1/resumes", files={"file": ("a.pdf", content, "application/pdf")})
    second = await client.post("/v1/resumes", files={"file": ("b.pdf", content, "application/pdf")})

    assert second.json()["resume_id"] == first.json()["resume_id"]
    assert second.json()["duplicate_of_existing"] is True
    assert len(no_real_queue) == 1


async def test_the_original_pdf_reaches_object_storage(
    client: AsyncClient, signed_in: str, no_real_queue: list[str]
) -> None:
    from careerlayer_api import storage

    content = read_fixture("clean-resume.pdf")
    response = await client.post(
        "/v1/resumes", files={"file": ("alex.pdf", content, "application/pdf")}
    )

    stored = storage.get(storage.original_key(response.json()["resume_id"]))
    assert stored == content


async def test_a_traversal_filename_is_reduced_to_its_base_name(
    client: AsyncClient, signed_in: str, no_real_queue: list[str]
) -> None:
    response = await client.post(
        "/v1/resumes",
        files={
            "file": (
                "../../etc/passwd.pdf",
                read_fixture("clean-resume.pdf"),
                "application/pdf",
            )
        },
    )

    assert response.json()["filename"] == "passwd.pdf"
