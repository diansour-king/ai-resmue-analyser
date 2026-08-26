import json
from decimal import Decimal
from pathlib import Path

import pytest

from careerlayer.scoring.cli import parse_scoring_payload, run_cli


def test_cli_with_dict_payload(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    payload = {
        "requirements": [
            {"id": "R1", "criticality": 3, "necessity": "required"},
            {"id": "R2", "criticality": 2, "necessity": "preferred"},
        ],
        "claims": [
            {
                "requirement_id": "R1",
                "met": True,
                "match_type": "direct",
                "evidence_spans": ["s1", "s2", "s3"],
            },
            {
                "requirement_id": "R2",
                "met": False,
                "match_type": "none",
            },
        ],
    }

    test_file = tmp_path / "test_match.json"
    test_file.write_text(json.dumps(payload), encoding="utf-8")

    # Run plain text CLI
    res = run_cli([str(test_file)])
    captured = capsys.readouterr()

    # w1 = 3.0, contrib = 3.0; w2 = 0.8, contrib = 0.0 -> total w = 3.8
    # score = 100 * 3.0 / 3.8 = 78.947... -> 78.9
    assert res.score == Decimal("78.9")
    assert "Match Score:       78.9" in captured.out

    # Run json CLI
    _ = run_cli([str(test_file), "--json"])
    captured_json = capsys.readouterr()

    data = json.loads(captured_json.out)
    assert data["score"] == "78.9"
    assert data["requirement_count"] == 2
    assert data["unmet_required_count"] == 0


def test_cli_with_list_payload(tmp_path: Path) -> None:
    payload = [
        {
            "id": "R1",
            "criticality": 2,
            "necessity": "required",
            "met": True,
            "match_type": "direct",
            "evidence_spans": ["s1"],
        }
    ]
    reqs, claims = parse_scoring_payload(payload)
    assert len(reqs) == 1
    assert len(claims) == 1
