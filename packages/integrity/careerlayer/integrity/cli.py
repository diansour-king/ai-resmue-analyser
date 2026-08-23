import argparse
import contextlib
import json
import sys
from pathlib import Path

from .detectors import REGISTRY, run
from .document import parse
from .errors import IntegrityError
from .models import Finding, ParsedDocument
from .rendered_layer import RENDER_DPI, ocr_is_available

_COLUMN_WIDTHS = (4, 5, 5, 5, 46)


def _configure_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            with contextlib.suppress(Exception):
                stream.reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    _configure_streams()
    args = _parser().parse_args(argv)
    if not args.path.is_file():
        print(f"no such file: {args.path}", file=sys.stderr)
        return 2

    try:
        document = parse(args.path, with_ocr=not args.no_ocr, dpi=args.dpi)
        findings = run(document, enabled=set(args.detectors) if args.detectors else None)
    except IntegrityError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(_as_payload(document, findings), indent=2))
    else:
        _print_table(document, findings)

    # A non-zero exit for anything above info, so this is usable as a check in a pipeline
    # without parsing the output.
    return 1 if any(finding.severity.value != "info" for finding in findings) else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m careerlayer.integrity",
        description="Report attempts to manipulate a reader hidden inside a PDF resume.",
    )
    parser.add_argument("path", type=Path, help="the PDF to analyse")
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    parser.add_argument(
        "--detectors",
        nargs="+",
        choices=sorted(REGISTRY),
        metavar="ID",
        help=f"run only these detectors ({', '.join(sorted(REGISTRY))})",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="skip the rendered-layer pass; D6 will not run",
    )
    parser.add_argument(
        "--dpi", type=int, default=RENDER_DPI, help=f"render resolution (default {RENDER_DPI})"
    )
    return parser


def _as_payload(document: ParsedDocument, findings: list[Finding]) -> dict[str, object]:
    return {
        "document": {
            "path": document.path,
            "page_count": document.page_count,
            "ocr_available": document.ocr_available,
        },
        "findings": [finding.model_dump(mode="json") for finding in findings],
        "summary": _counts(findings),
    }


def _counts(findings: list[Finding]) -> dict[str, int]:
    counts = {"high": 0, "suspicious": 0, "info": 0}
    for finding in findings:
        counts[finding.severity.value] += 1
    return counts


def _print_table(document: ParsedDocument, findings: list[Finding]) -> None:
    print(f"{document.path}  ({document.page_count} page(s))")
    if not document.ocr_available:
        print("  no OCR layer: D6 did not run, so hidden text with no other signal is missed")
    print()

    if not findings:
        print("No findings. The text layer and the rendered page agree.")
        return

    header = ("ID", "SEV", "CONF", "PAGE", "EXCERPT")
    print("  ".join(name.ljust(width) for name, width in zip(header, _COLUMN_WIDTHS, strict=True)))
    print("  ".join("-" * width for width in _COLUMN_WIDTHS))
    for finding in findings:
        row = (
            finding.detector_id,
            finding.severity.value[:5],
            f"{finding.confidence:.2f}",
            str(finding.page),
            _truncate(finding.excerpt, _COLUMN_WIDTHS[4]),
        )
        print("  ".join(cell.ljust(width) for cell, width in zip(row, _COLUMN_WIDTHS, strict=True)))

    print()
    counts = _counts(findings)
    print(f"{counts['high']} high, {counts['suspicious']} suspicious, {counts['info']} info")
    print()
    for index, finding in enumerate(findings, start=1):
        box = finding.bbox
        print(f"{index}. {finding.detector_id} {finding.detector_name} [{finding.severity.value}]")
        print(
            f"   page {finding.page} at ({box.x0:.0f}, {box.y0:.0f})"
            f" to ({box.x1:.0f}, {box.y1:.0f})"
        )
        print(f"   {finding.rationale}")
        print()


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def cli_entry() -> None:
    sys.exit(main())


__all__ = ["main", "ocr_is_available"]
