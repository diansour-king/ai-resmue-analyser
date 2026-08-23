from collections.abc import Callable

import pytest

from careerlayer.integrity import ParsedDocument
from careerlayer.integrity.detectors import extraction_delta

from .conftest import needs_ocr

Load = Callable[[str], ParsedDocument]


@needs_ocr
@pytest.mark.parametrize(
    "fixture",
    ["injected-invisible.pdf", "injected-low-contrast.pdf", "injected-micro-type.pdf"],
)
def test_text_absent_from_the_render_is_reported(with_ocr: Load, fixture: str) -> None:
    """D6 is the backstop: it catches these three without knowing how any of them work."""
    findings = extraction_delta.detect(with_ocr(fixture))

    assert len(findings) == 1
    assert "Ignore previous instructions" in findings[0].excerpt


@needs_ocr
@pytest.mark.parametrize("fixture", ["clean-resume.pdf", "clean-two-page.pdf"])
def test_clean_documents_produce_no_false_positives(with_ocr: Load, fixture: str) -> None:
    """The number that matters. OCR misreads clean text constantly and must be forgiven."""
    assert extraction_delta.detect(with_ocr(fixture)) == []


@needs_ocr
def test_the_floor_is_what_separates_signal_from_noise(with_ocr: Load) -> None:
    """The injected line aligns at about 49 out of 100; move the floor under it and it hides."""
    document = with_ocr("injected-invisible.pdf")

    assert extraction_delta.detect(document, similarity_floor=72.0) != []
    assert extraction_delta.detect(document, similarity_floor=40.0) == []


@needs_ocr
def test_the_margin_between_clean_and_injected_text_still_holds(with_ocr: Load) -> None:
    """Guards the threshold itself rather than its consequences.

    If a change to normalisation or candidate joining narrows this margin, the floor
    recorded in docs/decisions/0002 is stale and this fails before a false positive reaches
    anyone. The numbers are a floor and a ceiling, not the measured values, so ordinary OCR
    drift does not make this test flap.
    """
    worst_clean = min(
        score
        for fixture in ("clean-resume.pdf", "clean-two-page.pdf")
        for page in with_ocr(fixture).pages
        for _, score in extraction_delta.alignment_scores(page)
    )
    injected = [
        score
        for page in with_ocr("injected-invisible.pdf").pages
        for line, score in extraction_delta.alignment_scores(page)
        if "Ignore previous" in line.text
    ]

    assert worst_clean > 80.0
    assert injected and max(injected) < 60.0


def test_without_an_ocr_layer_the_detector_declines_to_run(text_only: Load) -> None:
    """With nothing to compare against every line is missing, which is a lie, not a finding."""
    assert extraction_delta.detect(text_only("injected-invisible.pdf")) == []


def test_normalisation_removes_the_differences_ocr_is_entitled_to_make() -> None:
    assert extraction_delta.normalise("  Python,   FastAPI!  ") == "python fastapi"
    assert extraction_delta.normalise("Redis Cache") == "redis cache"


def test_normalisation_folds_compatibility_characters() -> None:
    """NFKC first, so a no-break space or a ligature is not read as a missing line."""
    assert extraction_delta.normalise("Redis\u00a0Cache") == "redis cache"
    assert extraction_delta.normalise("of\ufb01ce") == "office"


@needs_ocr
def test_page_numbers_survive_a_page_break(with_ocr: Load) -> None:
    document = with_ocr("clean-two-page.pdf")

    assert document.page_count == 2
    assert [page.number for page in document.pages] == [1, 2]
