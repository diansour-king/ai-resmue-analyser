import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .engine import compute_match_score
from .models import ClaimInput, RequirementInput, ScoreResult


def parse_scoring_payload(
    data: dict[str, Any] | list[Any],
) -> tuple[list[RequirementInput], list[ClaimInput]]:
    """Parse JSON structure containing requirements and claims."""
    if isinstance(data, dict):
        reqs_raw = data.get("requirements", [])
        claims_raw = data.get("claims", [])
    elif isinstance(data, list):
        # List of requirements or claims with embedded specs
        reqs_raw = []
        claims_raw = []
        for item in data:
            if "criticality" in item or "necessity" in item:
                reqs_raw.append(item)
            if "met" in item or "match_type" in item:
                claims_raw.append(item)
    else:
        raise ValueError("Unsupported JSON payload format for scoring")

    requirements = [
        RequirementInput(
            id=str(r.get("id", f"req-{i}")),
            text=r.get("text"),
            criticality=int(r.get("criticality", 2)),
            necessity=r.get("necessity", "required"),
            weight=r.get("weight"),
        )
        for i, r in enumerate(reqs_raw)
    ]

    claims = [
        ClaimInput(
            requirement_id=str(c.get("requirement_id", "")),
            met=bool(c.get("met", False)),
            match_type=c.get("match_type", "none"),
            evidence_spans=c.get("evidence_spans", []),
            satisfaction=c.get("satisfaction"),
            corroboration=c.get("corroboration"),
            integrity_factor=c.get("integrity_factor"),
            evidence_quality=c.get("evidence_quality"),
            contribution=c.get("contribution"),
            confidence=c.get("confidence"),
            rationale=c.get("rationale"),
            adjacency_note=c.get("adjacency_note"),
        )
        for c in claims_raw
    ]

    return requirements, claims


def run_cli(args: list[str] | None = None) -> ScoreResult:
    parser = argparse.ArgumentParser(
        prog="careerlayer-scoring",
        description="Deterministic Match Scoring Engine CLI",
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="-",
        help="Path to JSON file containing requirements and claims (or - for stdin)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON result",
    )

    parsed = parser.parse_args(args)

    if parsed.file == "-":
        content = sys.stdin.read()
    else:
        content = Path(parsed.file).read_text(encoding="utf-8")

    payload = json.loads(content)
    requirements, claims = parse_scoring_payload(payload)

    result = compute_match_score(requirements, claims)

    if parsed.json:
        print(result.model_dump_json(indent=2))
    else:
        print(f"Match Score:       {result.score}")
        print(f"Score if Trusted:  {result.score_if_trusted}")
        print(f"Impact Delta:      {result.impact_delta}")
        print(f"Requirements:      {result.requirement_count}")
        print(f"Unmet Required:    {result.unmet_required_count}")
        print(f"Total Weight:      {result.total_weight}")
        print(f"Total Contrib:     {result.total_contribution}")

    return result


def main() -> int:
    try:
        run_cli()
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
