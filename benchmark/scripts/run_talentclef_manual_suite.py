"""Ejecuta la suite PDF TalentCLEF en un proceso y compara configuraciones."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.case_contract import build_case_request  # noqa: E402
from benchmark.metrics import macro_average  # noqa: E402


DEFAULT_SUITE = REPO_ROOT / "benchmark/results/manual_suites/talentclef-20-v1"
DEFAULT_KEYWORD_MULTIPLIERS = (2.5, 1.0)


def multiplier_tag(value: float) -> str:
    return f"{value:g}".replace("-", "m").replace(".", "p")


def variant_id(input_mode: str, keyword_multiplier: float) -> str:
    return f"{input_mode}-keyword-{keyword_multiplier:g}"


def result_filename(input_mode: str, keyword_multiplier: float) -> str:
    prefix = "local_pipeline" if input_mode == "criteria" else "local_pipeline_raw_offer"
    return f"{prefix}_kw_{multiplier_tag(keyword_multiplier)}_result.json"


def build_raw_offer_request(request: dict[str, Any]) -> dict[str, Any]:
    """Conserva la oferta completa y elimina toda expansion mediante criterios."""

    return build_case_request(
        str(request["job_description"]),
        [],
        categoria=str(request.get("categoria", "")),
        stack=str(request.get("stack", "")),
        strictness=str(request.get("strictness", "normal")),
        balance=0.5,
    )


def build_variant_summary(
    suite_manifest: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    input_mode: str,
    keyword_multiplier: float,
    wall_seconds: float,
) -> dict[str, Any]:
    manifest_cases = {row["case_id"]: row for row in suite_manifest["cases"]}
    rows: list[dict[str, Any]] = []
    for result in results:
        case = manifest_cases[result["case_id"]]
        rows.append(
            {
                "case_id": result["case_id"],
                "query_id": case["query_id"],
                "title": case["title"],
                "positive_count": case["positive_count"],
                "hard_negative_count": case["hard_negative_count"],
                "positive_shortfall": case["positive_shortfall"],
                "timing": result["timing"],
                "metrics": result["metrics"],
                "result_path": f"{case['path']}/{result_filename(input_mode, keyword_multiplier)}",
            }
        )
    metrics = macro_average(row["metrics"] for row in rows)
    timing_keys = ("parse_seconds", "score_seconds", "total_local_seconds")
    timing: dict[str, Any] = {
        "wall_seconds": round(wall_seconds, 4),
        "candidate_count": sum(row["timing"]["valid_candidates"] for row in rows),
    }
    for key in timing_keys:
        values = [float(row["timing"][key]) for row in rows]
        timing[key] = {
            "total": round(sum(values), 4),
            "mean_per_case": round(sum(values) / len(values), 4) if values else 0.0,
            "min": round(min(values), 4) if values else 0.0,
            "max": round(max(values), 4) if values else 0.0,
        }
    return {
        "variant_id": variant_id(input_mode, keyword_multiplier),
        "input_mode": input_mode,
        "keyword_multiplier": keyword_multiplier,
        "criteria_enabled": input_mode == "criteria",
        "is_api_control": input_mode == "criteria" and keyword_multiplier == 2.5,
        "macro_metrics": metrics,
        "timing": timing,
        "cases": rows,
    }


def build_summary(
    suite_manifest: dict[str, Any],
    variant_runs: list[dict[str, Any]],
    *,
    model_load_seconds: float,
    total_wall_seconds: float,
) -> dict[str, Any]:
    variants = [
        build_variant_summary(
            suite_manifest,
            run["results"],
            input_mode=str(run["input_mode"]),
            keyword_multiplier=float(run["keyword_multiplier"]),
            wall_seconds=float(run["wall_seconds"]),
        )
        for run in variant_runs
    ]
    control = next((row for row in variants if row["is_api_control"]), None)
    if control is None:
        raise ValueError("La comparacion requiere la variante control criteria con multiplier 2.5")
    comparisons: list[dict[str, Any]] = []
    for experiment in variants:
        if experiment is control:
            continue
        control_cases = {row["case_id"]: row for row in control["cases"]}
        case_deltas = []
        for row in experiment["cases"]:
            baseline = control_cases[row["case_id"]]
            case_deltas.append(
                {
                    "case_id": row["case_id"],
                    "query_id": row["query_id"],
                    "metrics": {
                        key: round(float(row["metrics"][key]) - float(baseline["metrics"][key]), 6)
                        for key in sorted(set(row["metrics"]) & set(baseline["metrics"]))
                    },
                }
            )
        comparisons.append(
            {
                "control_variant_id": control["variant_id"],
                "experiment_variant_id": experiment["variant_id"],
                "control_input_mode": control["input_mode"],
                "experiment_input_mode": experiment["input_mode"],
                "control_keyword_multiplier": control["keyword_multiplier"],
                "experiment_keyword_multiplier": experiment["keyword_multiplier"],
                "macro_metric_deltas": {
                    key: round(
                        float(experiment["macro_metrics"][key])
                        - float(control["macro_metrics"][key]),
                        6,
                    )
                    for key in sorted(
                        set(experiment["macro_metrics"]) & set(control["macro_metrics"])
                    )
                },
                "case_deltas": case_deltas,
            }
        )
    return {
        "schema_version": "1.0",
        "suite_id": suite_manifest["suite_id"],
        "task": "api_math_local_suite_comparison",
        "description": "PDF -> parsing -> scoring -> ranking; sin Gemini, HTTP ni frontend; un solo proceso y modelo.",
        "case_count": len(suite_manifest["cases"]),
        "known_exceptions": suite_manifest.get("known_exceptions", []),
        "timing": {
            "model_load_seconds": round(model_load_seconds, 4),
            "execution_wall_seconds": round(sum(row["timing"]["wall_seconds"] for row in variants), 4),
            "total_wall_seconds": round(total_wall_seconds, 4),
        },
        "variants": variants,
        "comparisons": comparisons,
    }


def _metric(value: float) -> str:
    return f"{value:.3f}"


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Suite {summary['suite_id']}",
        "",
        summary["description"],
        "",
        f"Casos por variante: **{summary['case_count']}** · Carga del modelo: "
        f"**{summary['timing']['model_load_seconds']:.4f} s** · Tiempo total: "
        f"**{summary['timing']['total_wall_seconds']:.4f} s**",
    ]
    for variant in summary["variants"]:
        if variant["is_api_control"]:
            label = "criterios confirmados, control API"
        elif variant["criteria_enabled"]:
            label = "criterios confirmados, experimento"
        else:
            label = "oferta completa sin criterios, experimento"
        lines.extend(
            [
                "",
                f"## {label} · keyword multiplier {variant['keyword_multiplier']:g}",
                "",
                "| Oferta | Pos/Neg | P@5 | P@10 | R@10 | nDCG@5 | nDCG@10 | MRR | Parse s | Score s | Total s |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in variant["cases"]:
            metrics = row["metrics"]
            timing = row["timing"]
            lines.append(
                f"| {row['query_id']} | {row['positive_count']}/{row['hard_negative_count']} "
                f"| {_metric(metrics['precision@5'])} | {_metric(metrics['precision@10'])} "
                f"| {_metric(metrics['recall@10'])} | {_metric(metrics['ndcg@5'])} "
                f"| {_metric(metrics['ndcg@10'])} | {_metric(metrics['mrr'])} "
                f"| {timing['parse_seconds']:.3f} | {timing['score_seconds']:.3f} "
                f"| {timing['total_local_seconds']:.3f} |"
            )
        macro = variant["macro_metrics"]
        timing = variant["timing"]
        lines.append(
            f"| **Macro / total** | — | {_metric(macro['precision@5'])} "
            f"| {_metric(macro['precision@10'])} | {_metric(macro['recall@10'])} "
            f"| {_metric(macro['ndcg@5'])} | {_metric(macro['ndcg@10'])} "
            f"| {_metric(macro['mrr'])} | {timing['parse_seconds']['total']:.3f} "
            f"| {timing['score_seconds']['total']:.3f} | {timing['total_local_seconds']['total']:.3f} |"
        )

    for comparison in summary["comparisons"]:
        delta = comparison["macro_metric_deltas"]
        lines.extend(
            [
                "",
                f"## Delta {comparison['experiment_variant_id']} vs {comparison['control_variant_id']}",
                "",
                "| Oferta | ΔP@5 | ΔP@10 | ΔnDCG@5 | ΔnDCG@10 | ΔMRR |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for row in comparison["case_deltas"]:
            metrics = row["metrics"]
            lines.append(
                f"| {row['query_id']} | {metrics['precision@5']:+.3f} "
                f"| {metrics['precision@10']:+.3f} | {metrics['ndcg@5']:+.3f} "
                f"| {metrics['ndcg@10']:+.3f} | {metrics['mrr']:+.3f} |"
            )
        lines.append(
            f"| **Macro** | {delta['precision@5']:+.3f} | {delta['precision@10']:+.3f} "
            f"| {delta['ndcg@5']:+.3f} | {delta['ndcg@10']:+.3f} | {delta['mrr']:+.3f} |"
        )

    if summary["known_exceptions"]:
        lines.extend(["", "## Excepciones conocidas", ""])
        for item in summary["known_exceptions"]:
            lines.append(f"- Query {item['query_id']}: {item['reason']}")
    lines.extend(
        [
            "",
            "El índice de Malaquías es una prioridad de ranking, no una probabilidad de contratación.",
            "",
        ]
    )
    return "\n".join(lines)


def run_suite(
    suite_dir: Path,
    keyword_multipliers: tuple[float, ...] = DEFAULT_KEYWORD_MULTIPLIERS,
) -> tuple[Path, Path]:
    suite_dir = suite_dir.resolve()
    manifest_path = suite_dir / "suite_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not keyword_multipliers or any(value <= 0 for value in keyword_multipliers):
        raise ValueError("Debe indicarse al menos un keyword multiplier positivo")
    keyword_multipliers = tuple(dict.fromkeys(float(value) for value in keyword_multipliers))
    if 2.5 not in keyword_multipliers:
        raise ValueError("La suite comparativa requiere keyword multiplier 2.5 como control")

    raw_requests: dict[str, Path] = {}
    for case in manifest["cases"]:
        case_dir = suite_dir / case["path"]
        request = json.loads((case_dir / "request.json").read_text(encoding="utf-8"))
        raw_path = case_dir / "request_raw_offer.json"
        raw_path.write_text(
            json.dumps(build_raw_offer_request(request), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raw_requests[case["case_id"]] = raw_path

    total_started = perf_counter()
    model_started = perf_counter()
    # Esta unica importacion carga SentenceTransformer una vez para todas las variantes y casos.
    from benchmark.scripts.run_local_pipeline_case import run_case

    model_load_seconds = perf_counter() - model_started
    variant_runs: list[dict[str, Any]] = []
    variant_specs = [
        ("criteria", keyword_multiplier) for keyword_multiplier in keyword_multipliers
    ]
    variant_specs.append(("raw_offer", 2.5))
    for input_mode, keyword_multiplier in variant_specs:
        variant_started = perf_counter()
        results: list[dict[str, Any]] = []
        for case in manifest["cases"]:
            case_dir = suite_dir / case["path"]
            output_path = case_dir / result_filename(input_mode, keyword_multiplier)
            request_path = raw_requests[case["case_id"]] if input_mode == "raw_offer" else None
            result_path = run_case(case_dir, output_path, request_path, keyword_multiplier)
            results.append(json.loads(result_path.read_text(encoding="utf-8")))
        variant_runs.append(
            {
                "input_mode": input_mode,
                "keyword_multiplier": keyword_multiplier,
                "wall_seconds": perf_counter() - variant_started,
                "results": results,
            }
        )
    total_wall_seconds = perf_counter() - total_started

    summary = build_summary(
        manifest,
        variant_runs,
        model_load_seconds=model_load_seconds,
        total_wall_seconds=total_wall_seconds,
    )
    json_path = suite_dir / "summary.json"
    markdown_path = suite_dir / "summary.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_summary_markdown(summary), encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument(
        "--keyword-multiplier",
        type=float,
        action="append",
        dest="keyword_multipliers",
        help="Repetible; por defecto ejecuta criterios 2.5/1.0 y siempre oferta cruda 2.5.",
    )
    args = parser.parse_args()
    multipliers = tuple(args.keyword_multipliers or DEFAULT_KEYWORD_MULTIPLIERS)
    json_path, markdown_path = run_suite(args.suite, multipliers)
    summary = json.loads(json_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "summary": str(json_path),
                "markdown": str(markdown_path),
                "timing": summary["timing"],
                "variants": [
                    {
                        "input_mode": row["input_mode"],
                        "keyword_multiplier": row["keyword_multiplier"],
                        "macro_metrics": row["macro_metrics"],
                    }
                    for row in summary["variants"]
                ],
                "comparisons": summary["comparisons"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
