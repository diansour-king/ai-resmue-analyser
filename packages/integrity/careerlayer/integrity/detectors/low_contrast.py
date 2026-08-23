from ..models import Finding, ParsedDocument, Severity, TextSpan
from ..text_layer import excerpt

DETECTOR_ID = "D2"
DETECTOR_NAME = "Low-contrast text"

CONTRAST_FLOOR = 1.6
_HIGH_SEVERITY_CONTRAST = 1.1
_ASSUMED_PAGE_BACKGROUND = (1.0, 1.0, 1.0)
_INVISIBLE_RENDER_MODE = 3


def detect(document: ParsedDocument, *, contrast_floor: float = CONTRAST_FLOOR) -> list[Finding]:
    """Text whose fill colour is too close to what is behind it to be read.

    Contrast is computed as the WCAG relative-luminance ratio, which ranges from 1.0 for
    identical colours to 21.0 for black on white. Body text normally sits above 4.5; the
    floor here is far lower because the goal is to catch text that is effectively invisible,
    not to audit accessibility, and flagging grey-on-white footnotes would be a false
    positive on half the resumes in the world.

    The background is assumed to be white rather than sampled from a page render. That is a
    deliberate limitation, recorded in docs/decisions/0003: sampling would catch white text
    over a dark banner, and would also cost a raster per page for a case that has not yet
    appeared in the corpus.
    """
    findings: list[Finding] = []
    for page in document.pages:
        for span in page.spans:
            if span.render_mode == _INVISIBLE_RENDER_MODE:
                continue  # D1 owns this span; two findings for one cause is noise.
            if not span.text.strip():
                continue
            ratio = contrast_ratio(_effective_colour(span), _ASSUMED_PAGE_BACKGROUND)
            if ratio >= contrast_floor:
                continue
            findings.append(
                Finding(
                    detector_id=DETECTOR_ID,
                    detector_name=DETECTOR_NAME,
                    severity=(
                        Severity.HIGH if ratio < _HIGH_SEVERITY_CONTRAST else Severity.SUSPICIOUS
                    ),
                    confidence=_confidence(ratio, contrast_floor),
                    page=page.number,
                    bbox=span.bbox,
                    excerpt=excerpt(span.text),
                    rationale=(
                        f"Contrast ratio {ratio:.2f}:1 against the page background, below the "
                        f"{contrast_floor:.1f}:1 floor. Fill colour "
                        f"{_hex(span.colour)} at {span.opacity:.0%} opacity is effectively "
                        "unreadable where it sits."
                    ),
                )
            )
    return findings


def _effective_colour(span: TextSpan) -> tuple[float, float, float]:
    """Blend the fill colour toward the background by its alpha.

    A fully opaque near-white glyph and a black glyph at 2% opacity are the same attack and
    should produce the same contrast number.
    """
    alpha = max(0.0, min(1.0, span.opacity))
    return tuple(  # type: ignore[return-value]
        span.colour[channel] * alpha + _ASSUMED_PAGE_BACKGROUND[channel] * (1.0 - alpha)
        for channel in range(3)
    )


def _relative_luminance(colour: tuple[float, float, float]) -> float:
    channels = []
    for value in colour:
        clamped = max(0.0, min(1.0, value))
        channels.append(
            clamped / 12.92 if clamped <= 0.04045 else ((clamped + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(
    foreground: tuple[float, float, float], background: tuple[float, float, float]
) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _confidence(ratio: float, floor: float) -> float:
    """Approach 1.0 as contrast approaches none at all, and 0.5 at the floor itself."""
    span = max(floor - 1.0, 1e-6)
    return round(min(1.0, 0.5 + 0.5 * (floor - ratio) / span), 3)


def _hex(colour: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, channel)) * 255):02x}" for channel in colour)
