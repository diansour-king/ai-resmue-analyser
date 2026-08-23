import re
import unicodedata

from rapidfuzz import fuzz, process

from ..models import Finding, Page, ParsedDocument, Severity, TextLine
from ..text_layer import excerpt

DETECTOR_ID = "D6"
DETECTOR_NAME = "Extraction delta"

# Tuned against the clean fixtures in tests/fixtures. See docs/decisions/0002 for the
# measurement behind this number and what it costs in recall.
SIMILARITY_FLOOR = 72.0

# Shorter lines than this are dropped rather than compared. OCR routinely loses a lone "•"
# or a two-letter state abbreviation, and at that length the similarity score is dominated
# by noise: "AWS" against "AVS" scores 67, which would flag a real line.
MIN_COMPARABLE_LENGTH = 12

_HIGH_SEVERITY_SIMILARITY = 30.0
_MAX_JOINED_OCR_LINES = 3
_WHITESPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]")


def detect(
    document: ParsedDocument, *, similarity_floor: float = SIMILARITY_FLOOR
) -> list[Finding]:
    """Text present in the text layer that nothing in the rendered page corresponds to.

    This is the detector that catches attacks the other five do not: any technique that
    makes text unreadable to a human while leaving it in the text layer shows up here, named
    or not.

    It is also the one that will produce the false positives if it is wrong, because OCR is
    noisy in ways that look exactly like an absent line. Three defences against that, in
    order of how much they matter:

    Normalisation first. Case, whitespace, punctuation and Unicode form are all things OCR
    gets wrong on text that is genuinely present, so none of them are allowed to contribute
    to the difference.

    Line alignment before token alignment. A text-layer line is compared against every OCR
    line on the same page, and against runs of up to three consecutive OCR lines joined
    together, because OCR splits a wrapped line as readily as it merges two. Only if the
    whole line fails to align are its tokens checked, which rescues a line whose ending OCR
    dropped.

    A length floor. Short lines are skipped entirely rather than compared badly.

    Documents with no OCR layer are skipped rather than reported: with nothing to compare
    against, every line is missing, and reporting that would be a lie about the document
    rather than a finding.
    """
    if not document.ocr_available:
        return []
    findings: list[Finding] = []
    for page in document.pages:
        if not page.ocr_lines:
            continue
        findings.extend(_page_findings(page, similarity_floor))
    return findings


def alignment_scores(page: Page) -> list[tuple[TextLine, float]]:
    """Every comparable line on the page with how well the rendered page corroborates it.

    Public because the threshold is an empirical choice, not a constant: the phase 4
    evaluation harness needs these scores to retune the floor against a real corpus, and the
    tests need them to assert on the margin between clean and injected text rather than on
    the floor happening to sit in the right place.

    Lines shorter than MIN_COMPARABLE_LENGTH are omitted rather than scored.
    """
    candidates = _ocr_candidates(page.ocr_lines)
    if not candidates:
        return []
    scored: list[tuple[TextLine, float]] = []
    for line in page.lines:
        normalised = normalise(line.text)
        if len(normalised) < MIN_COMPARABLE_LENGTH:
            continue
        # partial_ratio aligns a text-layer line that OCR read as part of a longer one.
        # token_set_ratio is the second chance: it forgives reordering and dropped words
        # that partial_ratio penalises, which rescues a line whose ending OCR lost.
        by_substring = process.extractOne(normalised, candidates, scorer=fuzz.partial_ratio)
        by_token = process.extractOne(normalised, candidates, scorer=fuzz.token_set_ratio)
        best = max(
            float(by_substring[1]) if by_substring else 0.0,
            float(by_token[1]) if by_token else 0.0,
        )
        scored.append((line, best))
    return scored


def _page_findings(page: Page, similarity_floor: float) -> list[Finding]:
    return [
        _finding(page, line, score, similarity_floor)
        for line, score in alignment_scores(page)
        if score < similarity_floor
    ]


def _ocr_candidates(ocr_lines: tuple[str, ...]) -> list[str]:
    """Every OCR line, plus each run of consecutive lines up to the join limit.

    OCR breaks a wrapped line in two about as often as it runs two together, so a
    text-layer line has to be allowed to match either shape.
    """
    normalised = [normalise(line) for line in ocr_lines]
    candidates = [line for line in normalised if line]
    for width in range(2, _MAX_JOINED_OCR_LINES + 1):
        for start in range(len(normalised) - width + 1):
            joined = " ".join(normalised[start : start + width]).strip()
            if joined:
                candidates.append(joined)
    return candidates


def normalise(text: str) -> str:
    """Strip every difference OCR is entitled to introduce on text that is really there."""
    decomposed = unicodedata.normalize("NFKC", text)
    without_punctuation = _PUNCTUATION.sub(" ", decomposed)
    return _WHITESPACE.sub(" ", without_punctuation).strip().casefold()


def _finding(page: Page, line: TextLine, score: float, similarity_floor: float) -> Finding:
    return Finding(
        detector_id=DETECTOR_ID,
        detector_name=DETECTOR_NAME,
        severity=Severity.HIGH if score < _HIGH_SEVERITY_SIMILARITY else Severity.SUSPICIOUS,
        confidence=round(min(1.0, 0.5 + 0.5 * (similarity_floor - score) / similarity_floor), 3),
        page=page.number,
        bbox=line.bbox,
        excerpt=excerpt(line.text),
        rationale=(
            f"Present in the PDF text layer with no counterpart in the rendered page. The "
            f"closest match anything on the page image produced scored {score:.0f} out of "
            f"100, against a floor of {similarity_floor:.0f}. A parser reads this line; a "
            "reader looking at the page does not."
        ),
    )
