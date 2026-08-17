"""Compara estrategias de ranking usando scores v2p2 ya persistidos.

No carga PDFs, embeddings ni Gemini. Eligibility se conserva como diagnóstico;
solo la estrategia A lo utiliza para ordenar.
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
)
from benchmark.experiments.threshold_grid import rethreshold_ranking
from benchmark.metrics import macro_average
from backend.app.scoring_core import rank_candidate_results


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ABLATION = (
    REPO_ROOT
    / "benchmark/results/ablations/talentclef-20-v1-criteria-lexical-v2p2"
)
FINALISTS = ("criteria-v1-lexical-v2", "criteria-v2-lexical-v2")
THRESHOLDS = (0.35, 0.40, 0.45, 0.50, 0.55)
DIAGNOSTIC_THRESHOLD = 0.55
FOCUS_QUERIES = {"91821", "96027"}

STRATEGIES = {
    "A_canonical": "eligibility_state, required_coverage, ranking_score",
    "B_ranking_score": "ranking_score continuo",
    "C_min_mean_score": "min_required, mean_required, ranking_score; tupla lexicográfica continua",
    "D_mean_score": "mean_required, ranking_score; tupla lexicográfica continua",
}


def required_score_summary(candidate: Mapping[str, Any]) -> dict[str, float | int]:
    components = candidate.get("score_components") or {}
    required = [
        float(row.get("score", 0.0))
        for row in components.get("criteria", []) or []
        if row.get("priority") == "required"
    ]
    if not required:
        return {"count": 0, "minimum": 0.0, "mean": 0.0}
    return {
        "count": len(required),
        "minimum": min(required),
        "mean": sum(required) / len(required),
    }


def _candidate_id(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("source_candidate_id") or candidate.get("candidate_id") or "")


def rank_with_strategy(
    candidates: Sequence[Mapping[str, Any]], strategy: str
) -> list[dict[str, Any]]:
    if strategy not in STRATEGIES:
        raise ValueError(f"estrategia desconocida: {strategy}")
    rows = copy.deepcopy(list(candidates))
    if strategy == "A_canonical":
        ordered = rank_candidate_results(rows)
    elif strategy == "B_ranking_score":
        ordered = sorted(
            rows,
            key=lambda row: (-float(row.get("ranking_score", 0.0)), _candidate_id(row)),
        )
    elif strategy == "C_min_mean_score":
        ordered = sorted(
            rows,
            key=lambda row: (
                -float(required_score_summary(row)["minimum"]),
                -float(required_score_summary(row)["mean"]),
                -float(row.get("ranking_score", 0.0)),
                _candidate_id(row),
            ),
        )
    else:
        ordered = sorted(
            rows,
            key=lambda row: (
                -float(required_score_summary(row)["mean"]),
                -float(row.get("ranking_score", 0.0)),
                _candidate_id(row),
            ),
        )
    return [
        dict(row, position=position)
        for position, row in enumerate(ordered, start=1)
    ]


def order_ids(ranking: Sequence[Mapping[str, Any]]) -> list[str]:
    return [_candidate_id(row) for row in ranking]


def strategy_orders_across_thresholds(
    ranking: Sequence[Mapping[str, Any]],
    strategy: str,
    thresholds: Sequence[float] = THRESHOLDS,
) -> dict[float, list[str]]:
    return {
        float(threshold): order_ids(
            rank_with_strategy(rethreshold_ranking(ranking, float(threshold)), strategy)
        )
        for threshold in thresholds
    }


def _load_overlay(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    from benchmark.adjudication.overlay import validate_overlay

    validate_overlay(payload)
    return payload


def _focus_rows(ranking: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for candidate in ranking[:10]:
        required = required_score_summary(candidate)
        rows.append(
            {
                "candidate_id": _candidate_id(candidate),
                "position": candidate["position"],
                "expected_relevance": candidate.get("expected_relevance"),
                "eligibility_state_at_0.55": candidate.get("eligibility_state"),
                "required_coverage_at_0.55": candidate.get("required_coverage"),
                "min_required": round(float(required["minimum"]), 6),
                "mean_required": round(float(required["mean"]), 6),
                "ranking_score": candidate.get("ranking_score"),
            }
        )
    return rows


def build_ranking_strategy_report(
    ablation_dir: Path,
    *,
    overlay_path: Path | None = DEFAULT_OVERLAY,
    thresholds: Sequence[float] = THRESHOLDS,
) -> dict[str, Any]:
    ablation_dir = ablation_dir.resolve()
    summary = json.loads((ablation_dir / "summary.json").read_text(encoding="utf-8"))
    variants = {row["variant_id"]: row for row in summary["variants"]}
    missing = [variant for variant in FINALISTS if variant not in variants]
    if missing:
        raise ValueError(f"finalistas ausentes: {', '.join(missing)}")
    overlay = _load_overlay(overlay_path)

    reports = []
    for variant_id in FINALISTS:
        source_variant = variants[variant_id]
        source_cases = []
        for case in source_variant["cases"]:
            source = json.loads(
                (ablation_dir / case["result_path"]).read_text(encoding="utf-8")
            )
            source_cases.append(source)

        strategy_reports = []
        for strategy, definition in STRATEGIES.items():
            cases = []
            stability_cases = []
            for source in source_cases:
                diagnostic_candidates = rethreshold_ranking(
                    source["ranking"], DIAGNOSTIC_THRESHOLD
                )
                ranking = rank_with_strategy(diagnostic_candidates, strategy)
                metrics, false_eligible = evaluate_case_ranking(
                    ranking, str(source["query_id"]), overlay
                )
                rates = eligibility_rates(ranking)
                orders = strategy_orders_across_thresholds(
                    source["ranking"], strategy, thresholds
                )
                unique_orders = {tuple(order) for order in orders.values()}
                reference = orders[DIAGNOSTIC_THRESHOLD]
                stability_cases.append(
                    {
                        "case_id": source["case_id"],
                        "query_id": str(source["query_id"]),
                        "invariant": len(unique_orders) == 1,
                        "unique_order_count": len(unique_orders),
                        "top10_overlap_vs_0.55": {
                            f"{threshold:.2f}": round(
                                len(set(order[:10]) & set(reference[:10])) / 10,
                                6,
                            )
                            for threshold, order in orders.items()
                        },
                    }
                )
                cases.append(
                    {
                        "case_id": source["case_id"],
                        "query_id": str(source["query_id"]),
                        "title": source["title"],
                        "metrics_by_view": metrics,
                        "eligibility_rates_at_0.55": rates,
                        "false_eligible_top10_by_view": false_eligible,
                        "top10": _focus_rows(ranking)
                        if str(source["query_id"]) in FOCUS_QUERIES
                        else None,
                    }
                )
            view_names = sorted(set.intersection(*(
                set(case["metrics_by_view"]) for case in cases
            )))
            strategy_reports.append(
                {
                    "strategy": strategy,
                    "definition": definition,
                    "uses_eligibility_for_sort": strategy == "A_canonical",
                    "macro_metrics_by_view": {
                        view: macro_average(
                            case["metrics_by_view"][view] for case in cases
                        )
                        for view in view_names
                    },
                    "eligibility_rates_at_0.55": aggregate_eligibility_rates(
                        [case["eligibility_rates_at_0.55"] for case in cases]
                    ),
                    "false_eligible_top10_total_by_view": {
                        view: sum(
                            case["false_eligible_top10_by_view"][view]["count"]
                            for case in cases
                        )
                        for view in view_names
                    },
                    "threshold_stability": {
                        "thresholds": [float(value) for value in thresholds],
                        "invariant": all(row["invariant"] for row in stability_cases),
                        "invariant_case_count": sum(row["invariant"] for row in stability_cases),
                        "case_count": len(stability_cases),
                        "cases": stability_cases,
                    },
                    "cases": cases,
                }
            )
        reports.append({"variant_id": variant_id, "strategies": strategy_reports})

    return {
        "schema_version": "1.0",
        "task": "posthoc_ranking_strategy",
        "source_ablation": str(ablation_dir),
        "uses_persisted_scores_only": True,
        "embeddings_loaded": False,
        "gemini_used": False,
        "diagnostic_eligibility_threshold": DIAGNOSTIC_THRESHOLD,
        "thresholds_for_stability": [float(value) for value in thresholds],
        "definitions": {
            "A": STRATEGIES["A_canonical"],
            "B": STRATEGIES["B_ranking_score"],
            "C": STRATEGIES["C_min_mean_score"],
            "D": STRATEGIES["D_mean_score"],
            "caveat": "experimento sobre el mismo suite; no promueve estrategia ni threshold",
        },
        "variants": reports,
    }


def render_ranking_strategy_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Estrategias de ranking post-hoc",
        "",
        "Usa scores v2p2 persistidos; no carga PDFs, MiniLM ni Gemini.",
        "Eligibility a 0,55 se conserva como diagnóstico. Solo A lo usa para ordenar.",
        "C y D son tuplas lexicográficas continuas, sin pesos ni threshold.",
    ]
    for variant in report["variants"]:
        lines.extend(
            [
                "",
                f"## {variant['variant_id']}",
                "",
                "| Estrategia | P@5 | P@10 | nDCG@10 | Pos eligible | Neg eligible | Falsos eligible top10 | Orden estable |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for strategy in variant["strategies"]:
            metrics = strategy["macro_metrics_by_view"]["original"]
            rates = strategy["eligibility_rates_at_0.55"]
            stability = strategy["threshold_stability"]
            lines.append(
                f"| {strategy['strategy']} | {metrics['precision@5']:.3f} | "
                f"{metrics['precision@10']:.3f} | {metrics['ndcg@10']:.3f} | "
                f"{rates['positive_eligible_rate']:.1%} | "
                f"{rates['negative_eligible_rate']:.1%} | "
                f"{strategy['false_eligible_top10_total_by_view']['original']} | "
                f"{'sí' if stability['invariant'] else 'no'} "
                f"({stability['invariant_case_count']}/{stability['case_count']}) |"
            )

        lines.extend(["", "### Casos 91821 y 96027", ""])
        for strategy in variant["strategies"]:
            lines.extend(
                [
                    f"#### {strategy['strategy']}",
                    "",
                    "| Query | P@5 | P@10 | nDCG@10 | Top 10 (id:label:estado) |",
                    "|---|---:|---:|---:|---|",
                ]
            )
            for case in strategy["cases"]:
                if case["query_id"] not in FOCUS_QUERIES:
                    continue
                metrics = case["metrics_by_view"]["original"]
                top = ", ".join(
                    f"{row['candidate_id']}:{row['expected_relevance']}:"
                    f"{'E' if row['eligibility_state_at_0.55'] == 'eligible' else 'R'}"
                    for row in case["top10"]
                )
                lines.append(
                    f"| {case['query_id']} | {metrics['precision@5']:.3f} | "
                    f"{metrics['precision@10']:.3f} | {metrics['ndcg@10']:.3f} | {top} |"
                )
    lines.extend(
        [
            "",
            "La estabilidad solo demuestra independencia del threshold; no demuestra calidad ni generalización.",
            "No promover una estrategia sin holdout y revisión humana.",
            "",
        ]
    )
    return "\n".join(lines)


def write_ranking_strategy_report(
    ablation_dir: Path,
    *,
    overlay_path: Path | None = DEFAULT_OVERLAY,
) -> tuple[Path, Path]:
    report = build_ranking_strategy_report(
        ablation_dir, overlay_path=overlay_path
    )
    json_path = ablation_dir / "ranking-strategy.json"
    markdown_path = ablation_dir / "ranking-strategy.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(
        render_ranking_strategy_markdown(report), encoding="utf-8"
    )
    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ablation", type=Path, default=DEFAULT_ABLATION)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    args = parser.parse_args()
    json_path, markdown_path = write_ranking_strategy_report(
        args.ablation, overlay_path=args.overlay
    )
    print(json.dumps({
        "json": str(json_path),
        "markdown": str(markdown_path),
        "uses_persisted_scores_only": True,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
