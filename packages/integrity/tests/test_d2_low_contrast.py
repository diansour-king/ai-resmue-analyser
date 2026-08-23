from collections.abc import Callable

from careerlayer.integrity import ParsedDocument, Severity
from careerlayer.integrity.detectors import low_contrast

Load = Callable[[str], ParsedDocument]


def test_white_on_white_is_high_severity(text_only: Load) -> None:
    findings = low_contrast.detect(text_only("injected-low-contrast.pdf"))

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert "Ignore previous instructions" in findings[0].excerpt
    assert "1.00:1" in findings[0].rationale


def test_black_body_text_is_not_flagged(text_only: Load) -> None:
    assert low_contrast.detect(text_only("clean-resume.pdf")) == []


def test_invisible_text_is_left_to_d1(text_only: Load) -> None:
    """One cause should produce one finding, not two with different explanations."""
    assert low_contrast.detect(text_only("injected-invisible.pdf")) == []


def test_contrast_ratio_endpoints() -> None:
    assert low_contrast.contrast_ratio((0, 0, 0), (1, 1, 1)) == 21.0
    assert low_contrast.contrast_ratio((1, 1, 1), (1, 1, 1)) == 1.0


def test_floor_is_a_parameter(text_only: Load) -> None:
    document = text_only("clean-resume.pdf")

    assert low_contrast.detect(document, contrast_floor=1.6) == []
    assert low_contrast.detect(document, contrast_floor=25.0) != []
