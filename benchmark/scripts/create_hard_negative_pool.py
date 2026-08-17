"""Congela positivos y los negativos mejor puntuados por una baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--negatives-per-query", type=int, default=20)
    args = parser.parse_args()
    if args.negatives_per_query < 1:
        raise ValueError("negatives-per-query debe ser positivo")
    report = json.loads(args.run.read_text(encoding="utf-8"))
    queries = {}
    for query in report["queries"]:
        positives = [str(row["candidate_id"]) for row in query["ranking"] if float(row["relevance"]) > 0]
        negatives = [str(row["candidate_id"]) for row in query["ranking"] if float(row["relevance"]) == 0]
        queries[query["query_id"]] = positives + negatives[:args.negatives_per_query]
    payload = {
        "schema_version": "1.0",
        "source_run_id": report["run_id"],
        "selection_rule": "all_positives_plus_highest_scoring_baseline_negatives",
        "negatives_per_query": args.negatives_per_query,
        "queries": queries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Pool: {args.output} ({len(queries)} queries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
