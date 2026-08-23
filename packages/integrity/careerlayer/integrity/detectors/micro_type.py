from ..models import Finding, ParsedDocument, Severity
from ..text_layer import excerpt

DETECTOR_ID = "D3"
DETECTOR_NAME = "Micro type"

READABILITY_FLOOR_PT = 4.0
_HIGH_SEVERITY_PT = 2.0
_INVISIBLE_RENDER_MODE = 3


def detect(
    document: ParsedDocument, *, readability_floor: float = READABILITY_FLOOR_PT
) -> list[Finding]:
    """Text set below the size at which a human could read it on paper or on screen.

    4pt is the starting floor from the build specification. Real resumes do legitimately go
    small: footer disclaimers and template watermarks land at 5 to 6pt, which is why the
    floor sits below them rather than at a comfortable reading size. The floor is a
    parameter so it can be retuned against the corpus in phase 4 without editing the
    detector.
    """
    findings: list[Finding] = []
    for page in document.pages:
        for span in page.spans:
            if span.render_mode == _INVISIBLE_RENDER_MODE:
                continue  # D1 owns it, and size is irrelevant to text that paints nothing.
            if not span.text.strip() or span.font_size >= readability_floor:
                continue
            findings.append(
                Finding(
                    detector_id=DETECTOR_ID,
                    detector_name=DETECTOR_NAME,
                    severity=(
                        Severity.HIGH if span.font_size < _HIGH_SEVERITY_PT else Severity.SUSPICIOUS
                    ),
                    confidence=_confidence(span.font_size, readability_floor),
                    page=page.number,
                    bbox=span.bbox,
                    excerpt=excerpt(span.text),
                    rationale=(
                        f"Set at {span.font_size:.2f}pt, below the {readability_floor:.1f}pt "
                        "readability floor. Text this small carries meaning to a parser and "
                        "none to a reader."
                    ),
                )
            )
    return findings


def _confidence(font_size: float, readability_floor: float) -> float:
    below = (readability_floor - font_size) / readability_floor
    return round(min(1.0, 0.5 + 0.5 * below), 3)
