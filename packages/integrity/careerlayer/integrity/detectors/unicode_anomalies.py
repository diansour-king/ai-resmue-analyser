import re
import unicodedata

from ..models import BBox, Finding, ParsedDocument, Severity, TextSpan

DETECTOR_ID = "D5"
DETECTOR_NAME = "Unicode anomalies"

# Written as escapes, not literals: a reviewer must be able to see these characters in the
# source, and by definition they are invisible when pasted in directly.
ZERO_WIDTH = frozenset(
    {
        "\u200b",  # zero width space
        "\u200c",  # zero width non-joiner
        "\u200d",  # zero width joiner
        "\u2060",  # word joiner
        "\ufeff",  # zero width no-break space
        "\u00ad",  # soft hyphen
    }
)
BIDI_CONTROLS = frozenset(
    {
        "\u202a",  # left-to-right embedding
        "\u202b",  # right-to-left embedding
        "\u202c",  # pop directional formatting
        "\u202d",  # left-to-right override
        "\u202e",  # right-to-left override
        "\u2066",  # left-to-right isolate
        "\u2067",  # right-to-left isolate
        "\u2068",  # first strong isolate
        "\u2069",  # pop directional isolate
    }
)

MIN_CONFUSABLE_WORDS = 2

_CONFUSABLE_SCRIPTS = ("CYRILLIC", "GREEK")
_MIN_WORD_LETTERS = 3
_CONTEXT_CHARS = 24
_WORD = re.compile(r"\w+", re.UNICODE)


def detect(
    document: ParsedDocument, *, min_confusable_words: int = MIN_CONFUSABLE_WORDS
) -> list[Finding]:
    """Invisible control characters, and letters wearing another script's clothes.

    Zero-width characters and bidi overrides are reported on sight. Neither has a reason to
    appear in a resume, and both make the text a parser reads diverge from the text a reader
    sees without changing a single visible glyph.

    Homoglyphs are judged per word rather than per span, and by script mixing rather than by
    density. A word that is Latin apart from a Cyrillic letter is a substitution; a document
    genuinely written in Cyrillic has no Latin to mix with and is left alone. Density across
    a span was the first approach and it does not survive contact with real PDFs: a document
    written by a single text-drawing pass is one span, so six substituted letters in a
    thousand fall below any useful threshold.
    """
    findings: list[Finding] = []
    for page in document.pages:
        for span in page.spans:
            findings.extend(_control_character_findings(page.number, span))
            confusable = _confusable_word_finding(page.number, span, min_confusable_words)
            if confusable is not None:
                findings.append(confusable)
    return findings


def _control_character_findings(page_number: int, span: TextSpan) -> list[Finding]:
    findings: list[Finding] = []
    zero_width = [index for index, char in enumerate(span.text) if char in ZERO_WIDTH]
    bidi = [index for index, char in enumerate(span.text) if char in BIDI_CONTROLS]

    if zero_width:
        findings.append(
            _finding(
                page_number,
                span,
                zero_width,
                Severity.SUSPICIOUS,
                0.9,
                f"Contains {len(zero_width)} zero-width character(s). They occupy no space on "
                "the page but split words for anything reading the text layer, which can hide "
                "a term from a reader while leaving it readable to a parser, or the reverse.",
            )
        )
    if bidi:
        findings.append(
            _finding(
                page_number,
                span,
                bidi,
                Severity.HIGH,
                0.95,
                f"Contains {len(bidi)} bidirectional override character(s). These reorder how "
                "text is displayed without changing its stored order, so the rendered line can "
                "read differently from the extracted one.",
            )
        )
    return findings


def _confusable_word_finding(page_number: int, span: TextSpan, minimum: int) -> Finding | None:
    mixed: list[tuple[int, int, str]] = []
    for match in _WORD.finditer(span.text):
        word = match.group()
        letters = [char for char in word if char.isalpha()]
        if len(letters) < _MIN_WORD_LETTERS:
            continue
        scripts = {_script_of(char) for char in letters}
        scripts.discard(None)
        if "LATIN" in scripts and scripts & set(_CONFUSABLE_SCRIPTS):
            mixed.append((match.start(), match.end(), word))
    if len(mixed) < minimum:
        return None

    indices = [index for start, end, _ in mixed for index in range(start, end)]
    sample = ", ".join(word for _, _, word in mixed[:4])
    return _finding(
        page_number,
        span,
        indices,
        Severity.SUSPICIOUS,
        round(min(1.0, 0.5 + 0.1 * len(mixed)), 3),
        f"{len(mixed)} word(s) mix Latin letters with a visually identical letter from "
        f"another script: {sample}. Substituted lookalikes read normally to a person and "
        "defeat an exact-match search for the words they sit in.",
    )


def _script_of(char: str) -> str | None:
    try:
        name = unicodedata.name(char)
    except ValueError:
        return None
    return name.split(" ", 1)[0]


def _finding(
    page_number: int,
    span: TextSpan,
    indices: list[int],
    severity: Severity,
    confidence: float,
    rationale: str,
) -> Finding:
    return Finding(
        detector_id=DETECTOR_ID,
        detector_name=DETECTOR_NAME,
        severity=severity,
        confidence=confidence,
        page=page_number,
        bbox=_box_around(span, indices),
        excerpt=_excerpt_around(span.text, indices),
        rationale=rationale,
    )


def _box_around(span: TextSpan, indices: list[int]) -> BBox:
    """Union of the neighbourhoods of each offending character.

    A zero-width character has a zero-width rectangle, so the box is grown to the characters
    on either side. Without that the overlay in the viewer would have nothing to draw.
    """
    box: BBox | None = None
    for index in indices:
        start = max(0, index - 1)
        end = min(len(span.text), index + 2)
        neighbourhood = span.box_over(start, end)
        box = neighbourhood if box is None else box.union(neighbourhood)
    return box if box is not None else span.bbox


def _excerpt_around(text: str, indices: list[int]) -> str:
    """A window around the offending characters, with the invisible ones made visible."""
    start = max(0, min(indices) - _CONTEXT_CHARS)
    end = min(len(text), max(indices) + 1 + _CONTEXT_CHARS)
    window = text[start:end]
    visible = "".join(
        f"<U+{ord(char):04X}>" if char in ZERO_WIDTH or char in BIDI_CONTROLS else char
        for char in window
    )
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + " ".join(visible.split()) + suffix
