from ..models import BBox, Finding, Page, ParsedDocument, Severity, TextSpan
from ..text_layer import excerpt

DETECTOR_ID = "D4"
DETECTOR_NAME = "Off-canvas or occluded text"

_VISIBLE_FRACTION_FLOOR = 0.5
_OCCLUSION_FRACTION = 0.95


def detect(document: ParsedDocument) -> list[Finding]:
    """Text placed where it cannot be seen: outside the crop box, or under a later image.

    Two mechanisms, one detector, because both answer the same question and a reviewer does
    not care which trick was used. Occlusion is decided by draw order rather than overlap
    alone: text over a background photograph is ordinary design, text under an image painted
    after it is hidden.
    """
    findings: list[Finding] = []
    for page in document.pages:
        for span in page.spans:
            if not span.text.strip():
                continue
            visible = span.bbox.contained_fraction(page.cropbox)
            if visible < _VISIBLE_FRACTION_FLOOR:
                findings.append(_off_canvas_finding(page, span, visible))
                continue
            covering = _covering_image(page, span)
            if covering is not None:
                findings.append(_occluded_finding(page, span, covering))
    return findings


def _off_canvas_finding(page: Page, span: TextSpan, visible: float) -> Finding:
    return Finding(
        detector_id=DETECTOR_ID,
        detector_name=DETECTOR_NAME,
        severity=Severity.HIGH if visible == 0.0 else Severity.SUSPICIOUS,
        confidence=round(min(1.0, 0.6 + 0.4 * (1.0 - visible)), 3),
        page=page.number,
        bbox=span.bbox,
        excerpt=excerpt(span.text),
        rationale=(
            f"Only {visible:.0%} of this text lies inside the page crop box, so a reader sees "
            f"{'none' if visible == 0.0 else 'almost none'} of it while the text layer "
            "carries all of it."
        ),
    )


def _occluded_finding(page: Page, span: TextSpan, covering: BBox) -> Finding:
    return Finding(
        detector_id=DETECTOR_ID,
        detector_name=DETECTOR_NAME,
        severity=Severity.HIGH,
        confidence=0.85,
        page=page.number,
        bbox=span.bbox,
        excerpt=excerpt(span.text),
        rationale=(
            "Covered by an image drawn after it, at "
            f"({covering.x0:.0f}, {covering.y0:.0f}) to ({covering.x1:.0f}, {covering.y1:.0f}). "
            "The text is painted first and then buried, so it survives extraction and not "
            "the eye."
        ),
    )


def _covering_image(page: Page, span: TextSpan) -> BBox | None:
    for seqno, rect in page.image_rects:
        if seqno <= span.seqno:
            continue
        if span.bbox.contained_fraction(rect) >= _OCCLUSION_FRACTION:
            return rect
    return None
