"""Crea una variante de inputs para un caso usando un catálogo de criterios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.case_contract import build_case_request, load_case_request  # noqa: E402


def create_variant(
    case_dir: Path,
    catalog_path: Path,
    query_id: str,
    output_path: Path,
) -> Path:
    case_dir = case_dir.resolve()
    truth = json.loads((case_dir / "ground_truth.json").read_text(encoding="utf-8"))
    base = load_case_request(case_dir, truth)
    catalog = json.loads(catalog_path.resolve().read_text(encoding="utf-8"))
    job = next(
        (row for row in catalog.get("jobs", []) if str(row.get("query_id")) == query_id),
        None,
    )
    if job is None:
        raise ValueError(f"La query {query_id} no existe en el catálogo")
    request = build_case_request(
        base["job_description"],
        job["criteria"],
        categoria=base["categoria"],
        stack=base["stack"],
        strictness=base["strictness"],
        balance=base["balance"],
    )
    request["criteria_catalog"] = {
        "catalog_id": catalog.get("catalog_id"),
        "criteria_version": catalog.get("criteria_version"),
        "query_id": query_id,
    }
    target = output_path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--query-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = create_variant(args.case_dir, args.catalog, args.query_id, args.output)
    print(f"Variante creada: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
