from collections.abc import Callable

from careerlayer.integrity import ParsedDocument, Severity
from careerlayer.integrity.detectors import invisible_render_mode

Load = Callable[[str], ParsedDocument]


def test_hidden_instruction_among_visible_text_is_high_severity(text_only: Load) -> None:
    findings = invisible_render_mode.detect(text_only("injected-invisible.pdf"))

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert "Ignore previous instructions" in findings[0].excerpt


def test_finding_carries_a_usable_page_and_box(text_only: Load) -> None:
    """Phase 2 draws this rectangle over a page render, so it has to be real."""
    document = text_only("injected-invisible.pdf")
    finding = invisible_render_mode.detect(document)[0]
    page = document.pages[finding.page - 1]

    assert finding.page == 1
    assert finding.bbox.width > 0
    assert finding.bbox.height > 0
    assert finding.bbox.contained_fraction(page.cropbox) > 0.9


def test_clean_resume_produces_nothing(text_only: Load) -> None:
    assert invisible_render_mode.detect(text_only("clean-resume.pdf")) == []


def test_visible_text_of_any_size_is_not_flagged(text_only: Load) -> None:
    """Micro type is D3's problem. D1 must not double-report it."""
    assert invisible_render_mode.detect(text_only("injected-micro-type.pdf")) == []
