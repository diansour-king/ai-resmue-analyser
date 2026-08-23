from collections.abc import Callable

import pytest

from careerlayer.integrity import ParsedDocument, run

from .conftest import needs_ocr

Load = Callable[[str], ParsedDocument]


@needs_ocr
@pytest.mark.parametrize("fixture", ["clean-resume.pdf", "clean-two-page.pdf"])
def test_a_clean_resume_produces_no_findings_at_all(with_ocr: Load, fixture: str) -> None:
    """The headline metric in miniature.

    A missed injection costs a company one wasted interview. A false flag costs a person a
    job. This test is the reason every threshold in the package sits where it does, and it
    is the one that should be hardest to keep passing as the corpus grows in phase 4.
    """
    findings = run(with_ocr(fixture))

    assert findings == [], [f"{f.detector_id}: {f.excerpt}" for f in findings]
