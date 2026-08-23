from careerlayer.integrity.models import BBox, Finding, Severity
from careerlayer_worker import skills


def span(text: str, page: int = 1, y: float = 100.0) -> skills.SpanRef:
    return skills.SpanRef(page=page, bbox=BBox(x0=72, y0=y, x1=400, y1=y + 10), text=text)


def flagged(page: int = 1, y: float = 100.0) -> Finding:
    return Finding(
        detector_id="D1",
        detector_name="Invisible render mode",
        severity=Severity.HIGH,
        confidence=0.95,
        page=page,
        bbox=BBox(x0=70, y0=y - 2, x1=410, y1=y + 12),
        excerpt="...",
        rationale="...",
    )


def test_a_term_is_found_and_pointed_at_its_span() -> None:
    matches = skills.extract([span("Built services in Python and FastAPI")], [])

    names = {match.canonical_name for match in matches}
    assert names == {"Python", "FastAPI"}
    assert all(match.span_indices == [0] for match in matches)


def test_substrings_do_not_count_as_matches() -> None:
    """Without whole-term matching, "Go" hits "Django" and the skill list becomes noise."""
    matches = skills.extract([span("Experienced with Django and Javanese literature")], [])

    assert {m.canonical_name for m in matches} == {"Django"}


def test_more_mentions_raise_confidence_but_never_to_certainty() -> None:
    once = skills.extract([span("Python")], [])[0]
    thrice = skills.extract([span("Python"), span("Python"), span("Python")], [])[0]

    assert once.confidence < thrice.confidence <= 0.9


def test_a_skill_evidenced_only_by_flagged_text_is_discounted_to_the_floor() -> None:
    """The product thesis in one assertion.

    A term that exists only where a human cannot see it must not read as a verified skill.
    """
    match = skills.extract([span("Kubernetes")], [flagged()])[0]

    assert match.flagged_support_count == 1
    assert match.confidence == 0.15


def test_clean_evidence_elsewhere_rescues_a_partly_flagged_skill() -> None:
    matches = skills.extract(
        [span("Kubernetes", y=100.0), span("Kubernetes", y=400.0)], [flagged(y=100.0)]
    )

    assert matches[0].support_count == 2
    assert matches[0].flagged_support_count == 1
    assert 0.15 < matches[0].confidence < 0.7


def test_a_finding_elsewhere_on_the_page_does_not_discount_a_clean_span() -> None:
    """Page granularity would punish the honest half of a document for the dishonest half."""
    match = skills.extract([span("Redis", y=600.0)], [flagged(y=100.0)])[0]

    assert match.flagged_support_count == 0
    assert match.confidence == 0.6


def test_confidence_is_reproducible_from_the_stored_counts() -> None:
    """Not an opaque score: the two numbers behind it are on the row."""
    match = skills.extract([span("Docker"), span("Docker")], [])[0]

    assert match.support_count == 2
    assert match.confidence == round(min(0.6 + 0.1 * (2 - 1), 0.9), 3)
