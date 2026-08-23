from collections.abc import Callable

from careerlayer.integrity import REGISTRY, ParsedDocument, run

Load = Callable[[str], ParsedDocument]


def test_every_detector_from_the_specification_is_registered() -> None:
    assert sorted(REGISTRY) == ["D1", "D2", "D3", "D4", "D5", "D6"]


def test_detectors_can_be_selected_individually(text_only: Load) -> None:
    document = text_only("injected-low-contrast.pdf")

    assert [f.detector_id for f in run(document, enabled={"D2"})] == ["D2"]
    assert run(document, enabled={"D3"}) == []


def test_findings_are_ordered_worst_first(text_only: Load) -> None:
    document = text_only("injected-unicode.pdf")
    severities = [f.severity.value for f in run(document)]

    assert severities == sorted(severities, key=["high", "suspicious", "info"].index)
