from ..models import Finding, Page, ParsedDocument, Severity
from ..text_layer import excerpt

DETECTOR_ID = "D1"
DETECTOR_NAME = "Invisible render mode"

_INVISIBLE_MODE = 3
_OCR_LAYER_SPAN_FRACTION = 0.9
_OCR_LAYER_IMAGE_COVERAGE = 0.5


def detect(document: ParsedDocument) -> list[Finding]:
    """Text drawn with render mode 3, which paints nothing.

    Render mode 3 is how every scanner puts a searchable text layer behind a page image, so
    it is not suspicious on its own. The page is classified first: a page that is almost
    entirely invisible text sitting on top of a full-page image is a scan, and its spans are
    reported at info severity so a reviewer sees them without being alarmed. Invisible text
    mixed into a page of ordinary visible text is the injection case.
    """
    findings: list[Finding] = []
    for page in document.pages:
        invisible = [span for span in page.spans if span.render_mode == _INVISIBLE_MODE]
        if not invisible:
            continue
        if _looks_like_a_scanned_page(page, len(invisible)):
            findings.append(_ocr_layer_finding(page, len(invisible)))
            continue
        findings.extend(
            Finding(
                detector_id=DETECTOR_ID,
                detector_name=DETECTOR_NAME,
                severity=Severity.HIGH,
                confidence=0.95,
                page=page.number,
                bbox=span.bbox,
                excerpt=excerpt(span.text),
                rationale=(
                    "Drawn with text render mode 3, which paints no pixels, on a page whose "
                    "other text is visible. The text is present to anything reading the PDF "
                    "text layer and absent to anyone looking at the page."
                ),
            )
            for span in invisible
        )
    return findings


def _looks_like_a_scanned_page(page: Page, invisible_count: int) -> bool:
    if not page.spans:
        return False
    if invisible_count / len(page.spans) < _OCR_LAYER_SPAN_FRACTION:
        return False
    page_area = page.cropbox.area
    if page_area <= 0:
        return False
    covered = max(
        (rect.intersection_area(page.cropbox) for _, rect in page.image_rects), default=0.0
    )
    return covered / page_area >= _OCR_LAYER_IMAGE_COVERAGE


def _ocr_layer_finding(page: Page, invisible_count: int) -> Finding:
    return Finding(
        detector_id=DETECTOR_ID,
        detector_name=DETECTOR_NAME,
        severity=Severity.INFO,
        confidence=0.8,
        page=page.number,
        bbox=page.cropbox,
        excerpt=excerpt(page.text),
        rationale=(
            f"All {invisible_count} text spans on this page are invisible and sit over a "
            "full-page image. This is the normal shape of a scanned document with a "
            "searchable text layer, not a hidden-text injection."
        ),
    )
