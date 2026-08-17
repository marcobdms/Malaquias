"""Ejecuta PDF -> parsing -> scoring -> ranking sin Gemini ni servidor HTTP."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.case_contract import load_case_request  # noqa: E402
from benchmark.metrics import evaluate_ranking  # noqa: E402
from benchmark.provenance import sha256_file  # noqa: E402
from backend.app.cv_parser import extract_text_from_pdf  # noqa: E402
from backend.app.job_criteria import (  # noqa: E402
    build_job_descriptions,
    build_scoring_criteria,
    parse_job_criteria,
)
from backend.app.matcher import score_cvs_to_criteria, score_cvs_to_job  # noqa: E402
from backend.app.scoring_core import rank_candidate_results  # noqa: E402
from backend.app.utils import clean_text, validate_pdf_text  # noqa: E402


def _engine_comparison(case_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    path = case_dir / "engine_result.json"
    if not path.exists():
        return None
    previous = json.loads(path.read_text(encoding="utf-8"))
    previous_order = [row["filename"] for row in previous.get("ranking", [])]
    current_order = [row["filename"] for row in rows]
    if not previous_order:
        return None
    limit = min(10, len(previous_order), len(current_order))
    overlap = len(set(previous_order[:limit]) & set(current_order[:limit]))
    previous_positions = {filename: index + 1 for index, filename in enumerate(previous_order)}
    changed = [
        {
            "filename": filename,
            "previous": previous_positions[filename],
            "current": index + 1,
        }
        for index, filename in enumerate(current_order)
        if filename in previous_positions and previous_positions[filename] != index + 1
    ]
    return {
        "source": str(path),
        "same_order": previous_order == current_order,
        f"top_{limit}_overlap": overlap / limit if limit else 0.0,
        "position_changes": changed,
    }


def run_case(
    case_dir: Path,
    output_path: Path | None = None,
    request_path: Path | None = None,
    keyword_multiplier: float = 2.5,
) -> Path:
    if keyword_multiplier <= 0:
        raise ValueError("keyword_multiplier debe ser positivo")
    case_dir = case_dir.resolve()
    truth_path = case_dir / "ground_truth.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    case_request = load_case_request(case_dir, truth, request_path)
    criteria = parse_job_criteria(json.dumps(case_request["criteria"], ensure_ascii=False))
    matching_description, _ = build_job_descriptions(case_request["job_description"], criteria)
    scoring_criteria = build_scoring_criteria(criteria)

    parse_started = perf_counter()
    parsed: list[dict[str, Any]] = []
    for index, metadata in enumerate(truth["candidates"]):
        pdf_path = case_dir / "cvs" / metadata["filename"]
        item_started = perf_counter()
        with pdf_path.open("rb") as handle:
            raw_text = extract_text_from_pdf(handle)
        valid = validate_pdf_text(raw_text)
        parsed.append({
            "candidate_id": f"cv-{index}",
            "filename": metadata["filename"],
            "source_candidate_id": metadata.get("candidate_id"),
            "expected_relevance": metadata.get("expected_relevance", 0),
            "clean": clean_text(raw_text) if valid else "",
            "parse_ms": round((perf_counter() - item_started) * 1000, 3),
        })
    parse_seconds = perf_counter() - parse_started

    valid_items = [item for item in parsed if item["clean"]]
    texts = [item["clean"] for item in valid_items]
    score_started = perf_counter()
    if scoring_criteria:
        scores = score_cvs_to_criteria(
            texts,
            scoring_criteria,
            strictness=case_request["strictness"],
            balance=case_request["balance"],
            keyword_multiplier=keyword_multiplier,
        )
    else:
        scores = score_cvs_to_job(
            texts,
            matching_description,
            strictness=case_request["strictness"],
            balance=case_request["balance"],
            keyword_multiplier=keyword_multiplier,
        )
    score_seconds = perf_counter() - score_started

    score_by_filename = {
        item["filename"]: score for item, score in zip(valid_items, scores, strict=True)
    }
    results: list[dict[str, Any]] = []
    for item in parsed:
        public = {
            key: item[key]
            for key in (
                "candidate_id",
                "filename",
                "source_candidate_id",
                "expected_relevance",
                "parse_ms",
            )
        }
        score = score_by_filename.get(item["filename"])
        if score is None:
            results.append({
                **public,
                "match_score": 0.0,
                "ranking_score": 0.0,
                "eligibility_state": "extraction_failed",
                "required_coverage": None,
                "score_components": None,
            })
            continue
        results.append({
            **public,
            "match_score": round(float(score["display_score"]) * 100, 2),
            "ranking_score": score["ranking_score"],
            "eligibility_state": score["eligibility_state"],
            "required_coverage": score["required_coverage"],
            "score_components": {
                "semantic_score": score["semantic_score"],
                "keyword_score": score["keyword_score"],
                "criteria": score["criteria_scores"],
            },
        })

    ranked = rank_candidate_results(results)
    relevance = {row["filename"]: row["expected_relevance"] for row in ranked}
    metrics = evaluate_ranking(
        [row["filename"] for row in ranked], relevance, cutoffs=(5, 10, 20)
    )
    selected_request_path = request_path.resolve() if request_path else case_dir / "request.json"
    output = {
        "schema_version": "2.0",
        "case_id": truth["case_id"],
        "task": "api_math_local" if keyword_multiplier == 2.5 else "math_experiment_local",
        "description": (
            "Mismo parsing, scoring y orden de la API; Gemini desactivado."
            if keyword_multiplier == 2.5
            else "Experimento local registrado; no representa la configuración activa de la API."
        ),
        "inputs": {
            "request": str(selected_request_path) if selected_request_path.exists() else "legacy offer.txt + criteria.json",
            "request_hash": sha256_file(selected_request_path) if selected_request_path.exists() else None,
            "ground_truth_hash": sha256_file(truth_path),
            "strictness": case_request["strictness"],
            "balance": case_request["balance"],
            "criteria_count": len(criteria),
            "candidate_count": len(ranked),
            "keyword_multiplier": keyword_multiplier,
        },
        "timing": {
            "parse_seconds": round(parse_seconds, 4),
            "score_seconds": round(score_seconds, 4),
            "total_local_seconds": round(parse_seconds + score_seconds, 4),
            "valid_candidates": len(valid_items),
        },
        "metrics": metrics,
        "engine_comparison": _engine_comparison(case_dir, ranked),
        "ranking": [dict(row, position=position) for position, row in enumerate(ranked, start=1)],
    }
    target = output_path.resolve() if output_path else case_dir / "local_pipeline_result.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--request", type=Path, help="Variante de inputs; por defecto request.json")
    parser.add_argument("--keyword-multiplier", type=float, default=2.5)
    args = parser.parse_args()
    path = run_case(args.case_dir, args.output, args.request, args.keyword_multiplier)
    result = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps({
        "result": str(path),
        "timing": result["timing"],
        "metrics": result["metrics"],
        "engine_comparison": result["engine_comparison"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
