import json
from pathlib import Path

import pytest

from careerlayer.integrity.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def test_clean_document_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    """The exit code is the contract for using this in a pipeline without parsing output."""
    code = main([str(FIXTURES / "clean-resume.pdf"), "--no-ocr"])

    assert code == 0
    assert "No findings" in capsys.readouterr().out


def test_injected_document_exits_non_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(FIXTURES / "injected-invisible.pdf"), "--no-ocr"])
    output = capsys.readouterr().out

    assert code == 1
    assert "D1" in output
    assert "high" in output


def test_json_output_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    main([str(FIXTURES / "injected-invisible.pdf"), "--no-ocr", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["document"]["page_count"] == 1
    assert payload["summary"] == {"high": 1, "suspicious": 0, "info": 0}

    finding = payload["findings"][0]
    assert finding["detector_id"] == "D1"
    assert finding["severity"] == "high"
    assert set(finding) == {
        "detector_id",
        "detector_name",
        "severity",
        "confidence",
        "page",
        "bbox",
        "excerpt",
        "rationale",
    }
    assert set(finding["bbox"]) == {"x0", "y0", "x1", "y1"}


def test_detector_selection_is_honoured(capsys: pytest.CaptureFixture[str]) -> None:
    main([str(FIXTURES / "injected-invisible.pdf"), "--no-ocr", "--json", "--detectors", "D3"])

    assert json.loads(capsys.readouterr().out)["findings"] == []


def test_missing_file_reports_and_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(FIXTURES / "does-not-exist.pdf")])

    assert code == 2
    assert "no such file" in capsys.readouterr().err


def test_a_file_that_is_not_a_pdf_fails_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    not_a_pdf = tmp_path / "resume.pdf"
    not_a_pdf.write_text("this is not a pdf")

    code = main([str(not_a_pdf)])

    assert code == 1
    assert "ExtractionFailed" in capsys.readouterr().err


def test_unicode_homoglyphs_print_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([str(FIXTURES / "injected-homoglyphs.pdf"), "--no-ocr"])
    output = capsys.readouterr().out

    assert code == 1
    assert "D5" in output
    assert "suspicious" in output
