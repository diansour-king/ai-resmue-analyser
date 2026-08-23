from collections.abc import Callable

from careerlayer.integrity import ParsedDocument, Severity
from careerlayer.integrity.detectors import unicode_anomalies

Load = Callable[[str], ParsedDocument]


def test_zero_width_characters_are_reported(text_only: Load) -> None:
    findings = unicode_anomalies.detect(text_only("injected-unicode.pdf"))
    zero_width = [f for f in findings if "zero-width" in f.rationale]

    assert len(zero_width) == 1
    assert zero_width[0].severity is Severity.SUSPICIOUS
    assert "<U+200B>" in zero_width[0].excerpt


def test_bidi_override_is_high_severity(text_only: Load) -> None:
    findings = unicode_anomalies.detect(text_only("injected-unicode.pdf"))
    bidi = [f for f in findings if "bidirectional" in f.rationale]

    assert len(bidi) == 1
    assert bidi[0].severity is Severity.HIGH
    assert "<U+202E>" in bidi[0].excerpt


def test_excerpt_renders_the_invisible_characters(text_only: Load) -> None:
    """A reviewer cannot judge a character they cannot see, so the excerpt escapes them."""
    for finding in unicode_anomalies.detect(text_only("injected-unicode.pdf")):
        assert "<U+" in finding.excerpt


def test_box_is_the_offending_region_not_the_whole_span(text_only: Load) -> None:
    """A zero-width character has a zero-width rectangle; the box must still be drawable."""
    document = text_only("injected-unicode.pdf")
    span_width = max(span.bbox.width for span in document.pages[0].spans)

    for finding in unicode_anomalies.detect(document):
        assert finding.bbox.width > 0
        assert finding.bbox.height > 0
        assert finding.bbox.width < span_width


def test_cyrillic_letters_inside_latin_words_are_reported(text_only: Load) -> None:
    findings = unicode_anomalies.detect(text_only("injected-homoglyphs.pdf"))
    mixed = [f for f in findings if "another script" in f.rationale]

    assert len(mixed) == 1
    assert mixed[0].severity is Severity.SUSPICIOUS


def test_clean_resume_produces_nothing(text_only: Load) -> None:
    assert unicode_anomalies.detect(text_only("clean-resume.pdf")) == []


def test_a_single_substituted_word_is_below_the_floor(text_only: Load) -> None:
    """One lookalike letter is a typo or a unit symbol. A pattern of them is an attack."""
    document = text_only("injected-homoglyphs.pdf")

    assert unicode_anomalies.detect(document, min_confusable_words=99) == []
    assert unicode_anomalies.detect(document, min_confusable_words=1) != []
