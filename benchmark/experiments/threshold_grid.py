"""Curva post-hoc de eligibility threshold sobre una ablación persistida.

No carga PDFs, embeddings ni Gemini. Reutiliza los scores por criterio guardados,
recalcula eligibility/coverage, vuelve a aplicar el orden canónico y mide el
trade-off entre cobertura de positivos y falsos positivos.
"""

from __future__ import annotations

import argparse
import copy
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from benchmark.experiments.ablation_runner import (
    DEFAULT_OVERLAY,
    aggregate_eligibility_rates,
    eligibility_rates,
    evaluate_case_ranking,
    false_eligible_top10,
    render_markdown,
)
from benchmark.metrics import macro_average
from backend.app.scoring_core import rank_candidate_results, required_eligibility


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ABLATION = (
    REPO_ROOT
    / "benchmark/results/ablations/talentclef-20-v1-criteria-lexical-v2p2"
)
FINALIST_VARIANTS = (
    "criteria-v1-lexical-v2",
    "criteria-v2-lexical-v2",
)
DEFAULT_THRESHOLDS = (0.35, 0.40, 0.45, 0.50, 0.55)


def rethreshold_ranking(
    ranking: Sequence[Mapping[str, Any]], threshold: float
) -> list[dict[str, Any]]:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold debe estar entre 0 y 1")
    rows = copy.deepcopy(list(ranking))
    for candidate in rows:
        components = candidate.get("score_components")
        if not components:
            candidate["eligibility_state"] = "extraction_failed"
            candidate["required_coverage"] = None
            continue
        criteria = components.get("criteria") or []
        for criterion in criteria:
            criterion["status"] = (
                "confirmed" if float(criterion.get("score", 0.0)) >= threshold else "unknown"
            )
        state, coverage = required_eligibility(criteria, threshold)
        candidate["eligibility_state"] = state
        candidate["required_coverage"] = (
            round(coverage, 6) if coverage is not None else None
        )
    return [
        dict(row, position=position)
        for position, row in enumerate(rank_candidate_results(rows), start=1)
    ]


def _load_overlay(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    from benchmark.adjudication.overlay import validate_overlay

    validate_overlay(payload)
    return payload


def enrich_ablation_summary(summary_path: Path) -> dict[str, Any]:
    """Añade gates de eligibility a un summary existente sin alterar rankings."""

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    root = summary_path.parent
    for variant in summary["variants"]:
        case_rates = []
        for case in variant["cases"]:
            result = json.loads((root / case["result_path"]).read_text(encoding="utf-8"))
            rates = eligibility_rates(result["ranking"])
            case["eligibility_rates"] = rates
            case_rates.append(rates)
        variant["eligibility_rates"] = aggregate_eligibility_rates(case_rates)
    summary["eligibility_gate_definition"] = {
        "positive_eligible_rate": "positivos originales con eligibility_state=eligible / positivos originales",
        "negative_eligible_rate": "negativos originales con eligibility_state=eligible / negativos originales",
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (root / "summary.md").write_text(render_markdown(summary), encoding="utf-8")
    return summary


def build_threshold_grid(
    ablation_dir: Path,
    *,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    variants: Sequence[str] = FINALIST_VARIANTS,
    overlay_path: Path | None = DEFAULT_OVERLAY,
) -> dict[str, Any]:
    ablation_dir = ablation_dir.resolve()
    summary_path = ablation_dir / "summary.json"
    summary = enrich_ablation_summary(summary_path)
    overlay = _load_overlay(overlay_path)
    available = {row["variant_id"]: row for row in summary["variants"]}
    missing = [variant for variant in variants if variant not in available]
    if missing:
        raise ValueError(f"Variantes ausentes: {', '.join(missing)}")
    threshold_values = tuple(dict.fromkeys(float(value) for value in thresholds))
    if not threshold_values or any(not 0.0 <= value <= 1.0 for value in threshold_values):
        raise ValueError("thresholds inválidos")

    variant_reports = []
    for variant_id in variants:
        source_variant = available[variant_id]
        threshold_reports = []
        for threshold in threshold_values:
            cases = []
            for case in source_variant["cases"]:
                source = json.loads(
                    (ablation_dir / case["result_path"]).read_text(encoding="utf-8")
                )
                ranking = rethreshold_ranking(source["ranking"], threshold)
                metrics, false_eligible = evaluate_case_ranking(
                    ranking, str(source["query_id"]), overlay
                )
                rates = eligibility_rates(ranking)
                cases.append(
                    {
                        "case_id": source["case_id"],
                        "query_id": str(source["query_id"]),
                        "metrics_by_view": metrics,
                        "eligibility_rates": rates,
                        "false_eligible_top10_by_view": false_eligible,
                        "ranking": [
                            {
                                "candidate_id": row["source_candidate_id"],
                                "position": row["position"],
                                "eligibility_state": row["eligibility_state"],
                                "required_coverage": row["required_coverage"],
                                "ranking_score": row["ranking_score"],
                            }
                            for row in ranking
                        ],
                    }
                )
            view_names = sorted(set.intersection(*(
                set(case["metrics_by_view"]) for case in cases
            )))
            threshold_reports.append(
                {
                    "threshold": threshold,
                    "macro_metrics_by_view": {
                        view: macro_average(
                            case["metrics_by_view"][view] for case in cases
                        )
                        for view in view_names
                    },
                    "eligibility_rates": aggregate_eligibility_rates(
                        [case["eligibility_rates"] for case in cases]
                    ),
                    "false_eligible_top10_total_by_view": {
                        view: sum(
                            case["false_eligible_top10_by_view"][view]["count"]
                            for case in cases
                        )
                        for view in view_names
                    },
                    "cases": cases,
                }
            )
        variant_reports.append(
            {"variant_id": variant_id, "thresholds": threshold_reports}
        )
    return {
        "schema_version": "1.0",
        "task": "posthoc_required_threshold_grid",
        "source_ablation": str(ablation_dir),
        "uses_persisted_scores_only": True,
        "embeddings_loaded": False,
        "gemini_used": False,
        "thresholds": list(threshold_values),
        "definitions": {
            "positive_eligible_rate": "positivos originales eligible / positivos originales",
            "negative_eligible_rate": "negativos originales eligible / negativos originales",
            "caveat": "curva de calibración sobre el mismo suite; no selecciona ni valida automáticamente un threshold",
        },
        "variants": variant_reports,
    }


def render_threshold_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Curva post-hoc del umbral required",
        "",
        "Usa scores por criterio ya persistidos: no carga PDFs, MiniLM ni Gemini.",
        "Esta es una curva de trade-off sobre el mismo conjunto, no una selección automática del umbral.",
    ]
    for variant in report["variants"]:
        lines.extend(
            [
                "",
                f"## {variant['variant_id']}",
                "",
                "| Threshold | P@5 | P@10 | nDCG@10 | Positivos eligible | Negativos eligible | Falsos eligible top10 |",
                "|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in variant["thresholds"]:
            metrics = row["macro_metrics_by_view"]["original"]
            rates = row["eligibility_rates"]
            lines.append(
                f"| {row['threshold']:.2f} | {metrics['precision@5']:.3f} | "
                f"{metrics['precision@10']:.3f} | {metrics['ndcg@10']:.3f} | "
                f"{rates['positive_eligible_rate']:.1%} "
                f"({rates['positive_eligible_count']}/{rates['positive_count']}) | "
                f"{rates['negative_eligible_rate']:.1%} "
                f"({rates['negative_eligible_count']}/{rates['negative_count']}) | "
                f"{row['false_eligible_top10_total_by_view']['original']} |"
            )
    lines.extend(["", "No promover un threshold sin validación holdout y revisión humana.", ""])
    return "\n".join(lines)


def write_threshold_grid(
    ablation_dir: Path,
    *,
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
    overlay_path: Path | None = DEFAULT_OVERLAY,
) -> tuple[Path, Path]:
    report = build_threshold_grid(
        ablation_dir, thresholds=thresholds, overlay_path=overlay_path
    )
    json_path = ablation_dir / "threshold-grid.json"
    markdown_path = ablation_dir / "threshold-grid.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_threshold_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ablation", type=Path, default=DEFAULT_ABLATION)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--threshold", type=float, action="append", dest="thresholds")
    args = parser.parse_args()
    json_path, markdown_path = write_threshold_grid(
        args.ablation,
        thresholds=tuple(args.thresholds or DEFAULT_THRESHOLDS),
        overlay_path=args.overlay,
    )
    report = json.loads(json_path.read_text(encoding="utf-8"))
    print(json.dumps({
        "json": str(json_path),
        "markdown": str(markdown_path),
        "uses_persisted_scores_only": report["uses_persisted_scores_only"],
        "thresholds": report["thresholds"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
