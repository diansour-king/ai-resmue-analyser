from collections.abc import Callable

from careerlayer.integrity import ParsedDocument, Severity
from careerlayer.integrity.detectors import micro_type

Load = Callable[[str], ParsedDocument]


def test_one_and_a_half_point_text_is_high_severity(text_only: Load) -> None:
    findings = micro_type.detect(text_only("injected-micro-type.pdf"))

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert "1.50pt" in findings[0].rationale


def test_ten_point_body_text_is_not_flagged(text_only: Load) -> None:
    assert micro_type.detect(text_only("clean-resume.pdf")) == []


def test_floor_is_a_parameter(text_only: Load) -> None:
    """The 4pt default is a starting point to be retuned in phase 4, not a constant."""
    document = text_only("clean-resume.pdf")

    assert micro_type.detect(document, readability_floor=4.0) == []
    assert micro_type.detect(document, readability_floor=12.0) != []
