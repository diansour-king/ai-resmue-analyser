from collections.abc import Callable

from careerlayer.integrity import ParsedDocument, Severity
from careerlayer.integrity.detectors import off_canvas

Load = Callable[[str], ParsedDocument]


def test_text_below_the_page_edge_is_high_severity(text_only: Load) -> None:
    findings = off_canvas.detect(text_only("injected-off-canvas.pdf"))

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert "crop box" in findings[0].rationale


def test_text_buried_under_a_later_image_is_flagged(text_only: Load) -> None:
    findings = off_canvas.detect(text_only("injected-occluded.pdf"))

    assert len(findings) == 1
    assert "drawn after it" in findings[0].rationale


def test_clean_resume_produces_nothing(text_only: Load) -> None:
    assert off_canvas.detect(text_only("clean-resume.pdf")) == []


def test_off_canvas_box_lies_outside_the_crop_box(text_only: Load) -> None:
    document = text_only("injected-off-canvas.pdf")
    finding = off_canvas.detect(document)[0]

    assert finding.bbox.contained_fraction(document.pages[0].cropbox) == 0.0
