"""Compara multiplicadores léxicos sobre el mismo caso, request y pool."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.scripts.run_local_pipeline_case import run_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--multipliers", type=float, nargs="+", default=[0.75, 1.0, 1.5, 2.5])
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for multiplier in args.multipliers:
        path = run_case(
            args.case_dir,
            output_dir / f"keyword-{multiplier:g}.json",
            args.request,
            multiplier,
        )
        result = json.loads(path.read_text(encoding="utf-8"))
        rows.append({
            "keyword_multiplier": multiplier,
            "result": str(path),
            "timing": result["timing"],
            "metrics": result["metrics"],
        })

    rows.sort(
        key=lambda row: (
            row["metrics"].get("ndcg@10", 0.0),
            row["metrics"].get("precision@10", 0.0),
        ),
        reverse=True,
    )
    summary = {
        "schema_version": "1.0",
        "task": "keyword_multiplier_grid",
        "case_dir": str(args.case_dir.resolve()),
        "request": str(args.request.resolve()),
        "ranking": rows,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
