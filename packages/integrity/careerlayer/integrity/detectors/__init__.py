from collections.abc import Callable

from ..models import Finding, ParsedDocument
from . import (
    extraction_delta,
    invisible_render_mode,
    low_contrast,
    micro_type,
    off_canvas,
    unicode_anomalies,
)

Detector = Callable[[ParsedDocument], list[Finding]]

# Ordered by detector id, which is also roughly cheapest first: the text-layer detectors are
# microseconds, D6 pays for an OCR pass that has already happened by the time it runs.
REGISTRY: dict[str, Detector] = {
    invisible_render_mode.DETECTOR_ID: invisible_render_mode.detect,
    low_contrast.DETECTOR_ID: low_contrast.detect,
    micro_type.DETECTOR_ID: micro_type.detect,
    off_canvas.DETECTOR_ID: off_canvas.detect,
    unicode_anomalies.DETECTOR_ID: unicode_anomalies.detect,
    extraction_delta.DETECTOR_ID: extraction_delta.detect,
}


def run(document: ParsedDocument, *, enabled: set[str] | None = None) -> list[Finding]:
    """Run every enabled detector and return findings ordered for a human to read.

    Detectors are independent by construction: none of them sees another's output, so one
    raising an exception is a bug in that detector rather than a reason to lose the rest.
    They are not wrapped in a try/except here for that reason. A detector that cannot decide
    returns no findings.
    """
    selected = REGISTRY if enabled is None else {k: v for k, v in REGISTRY.items() if k in enabled}
    findings = [finding for detect in selected.values() for finding in detect(document)]
    return sorted(findings, key=_reading_order)


def _reading_order(finding: Finding) -> tuple[int, float, float, str]:
    severity_rank = {"high": 0, "suspicious": 1, "info": 2}[finding.severity.value]
    return (severity_rank, finding.page, finding.bbox.y0, finding.detector_id)
