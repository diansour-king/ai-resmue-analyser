import uuid
from collections.abc import Callable

import pytest
from sqlalchemy import select

from careerlayer_api import storage
from careerlayer_api.models import (
    Extraction,
    FailureCode,
    Finding,
    ProcessingState,
    Resume,
    ResumePage,
    ResumeSkill,
    SkillEvidence,
    TextSpan,
)
from careerlayer_worker.db import session_scope
from careerlayer_worker.pipeline import process_resume

Uploaded = Callable[[str], str]


def test_a_clean_resume_processes_to_completion(uploaded: Uploaded) -> None:
    resume_id = uploaded("clean-resume.pdf")

    assert process_resume(resume_id) == "completed"

    with session_scope() as session:
        resume = session.get(Resume, uuid.UUID(resume_id))
        assert resume is not None
        assert resume.state == ProcessingState.COMPLETED
        assert resume.failure_code is None
        assert resume.page_count == 1


def test_pages_are_rendered_at_200_dpi_and_stored(uploaded: Uploaded) -> None:
    resume_id = uploaded("clean-resume.pdf")
    process_resume(resume_id)

    with session_scope() as session:
        page = session.execute(
            select(ResumePage).where(ResumePage.resume_id == uuid.UUID(resume_id))
        ).scalar_one()

        assert page.render_dpi == 200
        assert page.render_key == storage.page_render_key(resume_id, 1)
        # A4 at 200 DPI is about 1654 x 2339 pixels.
        assert 1600 < (page.render_width_px or 0) < 1700
        assert 2300 < (page.render_height_px or 0) < 2400

        png = storage.get(page.render_key)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_stored_pixel_geometry_matches_the_point_geometry(uploaded: Uploaded) -> None:
    """The overlay contract.

    The viewer computes its own scale from these two numbers. If they ever disagree with
    dpi/72 the overlay silently drifts, which is the one bug in this feature nobody would
    notice from a screenshot.
    """
    resume_id = uploaded("clean-resume.pdf")
    process_resume(resume_id)

    with session_scope() as session:
        page = session.execute(
            select(ResumePage).where(ResumePage.resume_id == uuid.UUID(resume_id))
        ).scalar_one()

    expected = (page.render_dpi or 0) / 72.0
    assert (page.render_width_px or 0) / page.width_pt == pytest.approx(expected, rel=0.01)
    assert (page.render_height_px or 0) / page.height_pt == pytest.approx(expected, rel=0.01)


def test_spans_and_an_extraction_record_are_persisted(uploaded: Uploaded) -> None:
    resume_id = uploaded("clean-resume.pdf")
    process_resume(resume_id)

    with session_scope() as session:
        extraction = session.execute(
            select(Extraction).where(Extraction.resume_id == uuid.UUID(resume_id))
        ).scalar_one()
        spans = list(
            session.execute(
                select(TextSpan).where(TextSpan.extraction_id == extraction.id)
            ).scalars()
        )

    assert extraction.page_count == 1
    assert extraction.duration_ms > 0
    assert len(spans) > 5
    assert all(span.x1 >= span.x0 and span.y1 >= span.y0 for span in spans)


def test_a_clean_resume_persists_no_findings(uploaded: Uploaded) -> None:
    resume_id = uploaded("clean-resume.pdf")
    process_resume(resume_id)

    with session_scope() as session:
        findings = list(
            session.execute(
                select(Finding).where(Finding.resume_id == uuid.UUID(resume_id))
            ).scalars()
        )

    assert findings == []


def test_hidden_text_survives_the_whole_pipeline_with_a_usable_box(
    uploaded: Uploaded,
) -> None:
    """The end-to-end assertion this phase exists for.

    A PDF with an invisible instruction goes in; a finding with a stable id and a rectangle
    the viewer can draw comes out, in PDF points, inside the page.
    """
    resume_id = uploaded("injected-invisible.pdf")
    process_resume(resume_id)

    with session_scope() as session:
        findings = list(
            session.execute(
                select(Finding).where(Finding.resume_id == uuid.UUID(resume_id))
            ).scalars()
        )
        page = session.execute(
            select(ResumePage).where(ResumePage.resume_id == uuid.UUID(resume_id))
        ).scalar_one()

    hidden = [f for f in findings if f.detector_id == "D1"]
    assert len(hidden) == 1
    finding = hidden[0]

    assert finding.id is not None
    assert finding.severity == "high"
    assert finding.page == 1
    assert "Ignore previous instructions" in finding.excerpt
    assert finding.rationale
    assert 0 <= finding.x0 < finding.x1 <= page.width_pt
    assert 0 <= finding.y0 < finding.y1 <= page.height_pt


def test_skills_are_persisted_with_evidence_pointing_at_real_spans(
    uploaded: Uploaded,
) -> None:
    resume_id = uploaded("clean-resume.pdf")
    process_resume(resume_id)

    with session_scope() as session:
        skills = list(
            session.execute(
                select(ResumeSkill).where(ResumeSkill.resume_id == uuid.UUID(resume_id))
            ).scalars()
        )
        names = {skill.canonical_name for skill in skills}
        links = list(
            session.execute(
                select(SkillEvidence).where(
                    SkillEvidence.skill_id.in_([skill.id for skill in skills])
                )
            ).scalars()
        )
        span_ids = set(session.execute(select(TextSpan.id)).scalars())

    assert {"Python", "FastAPI", "PostgreSQL", "Redis", "Docker"} <= names
    assert links, "a skill with no evidence link is exactly what this phase forbids"
    assert all(link.span_id in span_ids for link in links)
    assert all(skill.source == "dictionary_v1" for skill in skills)


def test_reprocessing_replaces_rather_than_duplicates(uploaded: Uploaded) -> None:
    """A retried job must not double every finding."""
    resume_id = uploaded("injected-invisible.pdf")
    process_resume(resume_id)
    process_resume(resume_id)

    with session_scope() as session:
        findings = list(
            session.execute(
                select(Finding).where(Finding.resume_id == uuid.UUID(resume_id))
            ).scalars()
        )
        pages = list(
            session.execute(
                select(ResumePage).where(ResumePage.resume_id == uuid.UUID(resume_id))
            ).scalars()
        )

    assert len(pages) == 1
    assert len([f for f in findings if f.detector_id == "D1"]) == 1


def test_a_corrupt_pdf_fails_with_a_safe_classification(uploaded: Uploaded) -> None:
    """The user learns the class of failure. The exception goes to the log and stops there."""
    resume_id = uploaded("clean-resume.pdf")
    with session_scope() as session:
        resume = session.get(Resume, uuid.UUID(resume_id))
        assert resume is not None
        storage.put(resume.storage_key, b"not a pdf at all", "application/pdf")

    assert process_resume(resume_id) == "failed"

    with session_scope() as session:
        resume = session.get(Resume, uuid.UUID(resume_id))
        assert resume is not None
        assert resume.state == ProcessingState.FAILED
        assert resume.failure_code == FailureCode.EXTRACTION_FAILED


def test_a_missing_resume_is_not_an_error(uploaded: Uploaded) -> None:
    assert process_resume(str(uuid.uuid4())) == "missing"


def test_a_two_page_document_keeps_its_page_numbers(uploaded: Uploaded) -> None:
    resume_id = uploaded("clean-two-page.pdf")
    process_resume(resume_id)

    with session_scope() as session:
        pages = list(
            session.execute(
                select(ResumePage)
                .where(ResumePage.resume_id == uuid.UUID(resume_id))
                .order_by(ResumePage.page_number)
            ).scalars()
        )

    assert [page.page_number for page in pages] == [1, 2]
    assert all(page.render_key for page in pages)
