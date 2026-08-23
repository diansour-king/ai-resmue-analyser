from collections.abc import Callable
from pathlib import Path

import pytest

from careerlayer.integrity import ParsedDocument, parse
from careerlayer.integrity.rendered_layer import ocr_is_available

FIXTURES = Path(__file__).parent / "fixtures"

needs_ocr = pytest.mark.skipif(
    not ocr_is_available(), reason="the tesseract binary is not installed"
)


@pytest.fixture(scope="session")
def text_only() -> Callable[[str], ParsedDocument]:
    """Parse a fixture without the OCR pass.

    Five of the six detectors read only the text layer, and skipping OCR takes their tests
    from seconds to milliseconds. Session-scoped and memoised because parsing the same
    fixture once per test is the slowest thing in this suite.
    """
    cache: dict[str, ParsedDocument] = {}

    def load(name: str) -> ParsedDocument:
        if name not in cache:
            cache[name] = parse(FIXTURES / name, with_ocr=False)
        return cache[name]

    return load


@pytest.fixture(scope="session")
def with_ocr() -> Callable[[str], ParsedDocument]:
    cache: dict[str, ParsedDocument] = {}

    def load(name: str) -> ParsedDocument:
        if name not in cache:
            cache[name] = parse(FIXTURES / name, with_ocr=True)
        return cache[name]

    return load
