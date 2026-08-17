"""Audit criterion discrimination in paired local-pipeline benchmark runs.

The module intentionally depends only on the Python standard library. It reads
already-produced pipeline results, so running an audit never invokes the model,
Gemini, PDF parsing, or the scoring engine.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CONFIG_FILES = {
    "kw1.0": "local_pipeline_kw_1_result.json",
    "kw2.5": "local_pipeline_kw_2p5_result.json",
}
COMPONENTS = ("semantic_score", "keyword_score", "score")
COMPONENT_LABELS = {
    "semantic_score": "semantic",
    "keyword_score": "keyword",
    "score": "hybrid",
}


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _variance(values: list[float]) -> float | None:
    return statistics.pvariance(values) if values else None


def _round(value: float | None, digits: int = 6) -> float | None:
    return None if value is None else round(value, digits)


def pairwise_auc(positive: Iterable[float], negative: Iterable[float]) -> float | None:
    """Return P(positive > negative), giving half credit to tied pairs."""

    positives = list(positive)
    negatives = list(negative)
    if not positives or not negatives:
        return None
    wins = 0.0
    for positive_score in positives:
        for negative_score in negatives:
            if positive_score > negative_score:
                wins += 1.0
            elif math.isclose(positive_score, negative_score, abs_tol=1e-12):
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def _first_evidence(criterion: dict[str, Any]) -> Any | None:
    """Use persisted evidence when present; never infer it from a score."""

    for key in ("evidence", "evidence_text", "evidence_snippet", "snippet", "matched_text"):
        value = criterion.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _criterion_records(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    records: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in result.get("ranking", []):
        relevance = int(candidate.get("expected_relevance", 0))
        for criterion in candidate.get("score_components", {}).get("criteria", []):
            records[str(criterion["id"])].append(
                {
                    "criterion_id": str(criterion["id"]),
                    "label": criterion.get("label", str(criterion["id"])),
                    "priority": criterion.get("priority", "unknown"),
                    "candidate_id": candidate.get("source_candidate_id") or candidate.get("candidate_id"),
                    "filename": candidate.get("filename"),
                    "position": candidate.get("position"),
                    "expected_relevance": relevance,
                    "status": criterion.get("status"),
                    "semantic_score": criterion.get("semantic_score"),
                    "keyword_score": criterion.get("keyword_score"),
                    "score": criterion.get("score"),
                    "evidence": _first_evidence(criterion),
                }
            )
    return records


def _component_stats(records: list[dict[str, Any]], component: str) -> dict[str, Any]:
    values = [float(row[component]) for row in records if row.get(component) is not None]
    positives = [float(row[component]) for row in records if row.get(component) is not None and row["expected_relevance"] > 0]
    negatives = [float(row[component]) for row in records if row.get(component) is not None and row["expected_relevance"] <= 0]
    positive_mean = _mean(positives)
    negative_mean = _mean(negatives)
    return {
        "mean": _round(_mean(values)),
        "variance": _round(_variance(values)),
        "positive_mean": _round(positive_mean),
        "negative_mean": _round(negative_mean),
        "positive_minus_negative": _round(
            None if positive_mean is None or negative_mean is None else positive_mean - negative_mean
        ),
        "pairwise_auc": _round(pairwise_auc(positives, negatives)),
    }


def _criterion_stats(case_id: str, config: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    keyword_values = [float(row["keyword_score"]) for row in records if row.get("keyword_score") is not None]
    evidence = [
        {
            "candidate_id": row["candidate_id"],
            "position": row["position"],
            "evidence": row["evidence"],
        }
        for row in records
        if row.get("evidence") is not None
    ]
    saturation = (
        sum(value >= 1.0 - 1e-9 for value in keyword_values) / len(keyword_values)
        if keyword_values
        else None
    )
    confirmed = [row.get("status") == "confirmed" for row in records]
    component_stats = {
        COMPONENT_LABELS[component]: _component_stats(records, component)
        for component in COMPONENTS
    }
    hybrid = component_stats["hybrid"]
    reasons: list[str] = []
    if saturation is not None and saturation >= 0.8:
        reasons.append("keyword_saturation_gte_80pct")
    if hybrid["variance"] is not None and hybrid["variance"] <= 0.0025:
        reasons.append("low_hybrid_variance")
    if hybrid["positive_minus_negative"] is not None and abs(hybrid["positive_minus_negative"]) < 0.03:
        reasons.append("hybrid_label_gap_below_0.03")
    if hybrid["pairwise_auc"] is not None and 0.45 <= hybrid["pairwise_auc"] <= 0.55:
        reasons.append("hybrid_auc_near_random")

    positives = [row for row in records if row["expected_relevance"] > 0]
    negatives = [row for row in records if row["expected_relevance"] <= 0]
    top_positive = min(positives, key=lambda row: row["position"]) if positives else None
    top_negative = min(negatives, key=lambda row: row["position"]) if negatives else None
    return {
        "case_id": case_id,
        "config": config,
        "criterion_id": records[0]["criterion_id"],
        "label": records[0]["label"],
        "priority": records[0]["priority"],
        "candidate_count": len(records),
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "keyword_saturation_rate": _round(saturation),
        "confirmed_rate": _round(sum(confirmed) / len(confirmed) if confirmed else None),
        "components": component_stats,
        "positions": {
            "top_positive": None if top_positive is None else {
                "candidate_id": top_positive["candidate_id"],
                "position": top_positive["position"],
            },
            "top_negative": None if top_negative is None else {
                "candidate_id": top_negative["candidate_id"],
                "position": top_negative["position"],
            },
        },
        "evidence_available": bool(evidence),
        "evidence_samples": evidence[:5],
        "non_discriminant": bool(reasons),
        "non_discriminant_reasons": reasons,
    }


def audit_suite(suite_dir: Path) -> dict[str, Any]:
    cases = sorted(path for path in suite_dir.iterdir() if path.is_dir())
    criteria: list[dict[str, Any]] = []
    loaded_cases: dict[str, list[str]] = defaultdict(list)
    missing: list[dict[str, str]] = []

    for case_dir in cases:
        for config, filename in CONFIG_FILES.items():
            result_path = case_dir / filename
            if not result_path.exists():
                missing.append({"case_id": case_dir.name, "config": config, "path": str(result_path)})
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            loaded_cases[config].append(case_dir.name)
            for records in _criterion_records(result).values():
                criteria.append(_criterion_stats(case_dir.name, config, records))

    criteria.sort(key=lambda row: (row["case_id"], row["criterion_id"], row["config"]))
    by_key = {(row["case_id"], row["criterion_id"], row["config"]): row for row in criteria}
    comparisons: list[dict[str, Any]] = []
    identities = sorted({(row["case_id"], row["criterion_id"]) for row in criteria})
    for case_id, criterion_id in identities:
        low = by_key.get((case_id, criterion_id, "kw1.0"))
        high = by_key.get((case_id, criterion_id, "kw2.5"))
        if not low or not high:
            continue
        comparisons.append(
            {
                "case_id": case_id,
                "criterion_id": criterion_id,
                "label": low["label"],
                "kw2.5_minus_kw1.0": {
                    "keyword_saturation_rate": _round(high["keyword_saturation_rate"] - low["keyword_saturation_rate"]),
                    "confirmed_rate": _round(high["confirmed_rate"] - low["confirmed_rate"]),
                    "hybrid_positive_minus_negative": _round(
                        high["components"]["hybrid"]["positive_minus_negative"]
                        - low["components"]["hybrid"]["positive_minus_negative"]
                    ),
                    "hybrid_pairwise_auc": _round(
                        high["components"]["hybrid"]["pairwise_auc"]
                        - low["components"]["hybrid"]["pairwise_auc"]
                    ),
                },
            }
        )

    summaries: dict[str, Any] = {}
    for config in CONFIG_FILES:
        rows = [row for row in criteria if row["config"] == config]
        saturation = [row["keyword_saturation_rate"] for row in rows if row["keyword_saturation_rate"] is not None]
        aucs = [row["components"]["hybrid"]["pairwise_auc"] for row in rows if row["components"]["hybrid"]["pairwise_auc"] is not None]
        summaries[config] = {
            "case_count": len(set(loaded_cases[config])),
            "criterion_count": len(rows),
            "mean_keyword_saturation_rate": _round(_mean(saturation)),
            "fully_saturated_criteria": sum(value >= 1.0 - 1e-9 for value in saturation),
            "criteria_saturated_gte_80pct": sum(value >= 0.8 for value in saturation),
            "non_discriminant_criteria": sum(row["non_discriminant"] for row in rows),
            "mean_hybrid_pairwise_auc": _round(_mean(aucs)),
            "criteria_with_persisted_evidence": sum(row["evidence_available"] for row in rows),
        }

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_suite": str(suite_dir.resolve()),
        "definitions": {
            "positive_label": "expected_relevance > 0",
            "keyword_saturation": "fraction of candidates with keyword_score == 1.0",
            "pairwise_auc": "P(score_positive > score_negative), ties count as 0.5",
            "non_discriminant_flags": {
                "keyword_saturation_gte_80pct": ">= 80% candidates have keyword_score 1.0",
                "low_hybrid_variance": "population variance <= 0.0025",
                "hybrid_label_gap_below_0.03": "absolute positive-negative hybrid mean gap < 0.03",
                "hybrid_auc_near_random": "hybrid pairwise AUC between 0.45 and 0.55",
            },
            "label_caveat": "TalentCLEF labels may be noisy; structural flags are not proof of human irrelevance.",
        },
        "configs": summaries,
        "missing_inputs": missing,
        "criteria": criteria,
        "comparisons": comparisons,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Auditoría reproducible de criterios",
        "",
        f"Fuente: `{report['source_suite']}`",
        "",
        "Esta auditoría reutiliza resultados ya generados. No ejecuta Gemini, parsing de PDF ni scoring.",
        "TalentCLEF se usa como señal auxiliar: una discrepancia con sus etiquetas no demuestra por sí sola un error del motor.",
        "",
        "## Resumen por configuración",
        "",
        "| Configuración | Casos | Criterios | Saturación media | Saturados 100% | Saturados >=80% | Marcados no discriminantes | AUC híbrida media | Evidencia persistida |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for config, summary in report["configs"].items():
        lines.append(
            f"| {config} | {summary['case_count']} | {summary['criterion_count']} | "
            f"{summary['mean_keyword_saturation_rate']:.1%} | {summary['fully_saturated_criteria']} | "
            f"{summary['criteria_saturated_gte_80pct']} | {summary['non_discriminant_criteria']} | "
            f"{summary['mean_hybrid_pairwise_auc']:.3f} | {summary['criteria_with_persisted_evidence']} |"
        )

    low = report["configs"].get("kw1.0", {})
    high = report["configs"].get("kw2.5", {})
    lines.extend(["", "## Lectura principal", ""])
    if low and high:
        change = high["mean_keyword_saturation_rate"] - low["mean_keyword_saturation_rate"]
        lines.append(
            f"Al pasar de `kw1.0` a `kw2.5`, la saturación léxica media cambia "
            f"de {low['mean_keyword_saturation_rate']:.1%} a {high['mean_keyword_saturation_rate']:.1%} "
            f"({change:+.1%})."
        )
        lines.append(
            f"Los criterios saturados en al menos el 80% del pool pasan de "
            f"{low['criteria_saturated_gte_80pct']} a {high['criteria_saturated_gte_80pct']}."
        )
    lines.append(
        "`no discriminante` es una alerta de auditoría, no una sentencia: combina saturación, "
        "varianza, separación de etiquetas y AUC, y debe revisarse con criterio humano."
    )
    lines.append(
        "Este suite no guardó fragmentos de evidencia por criterio; sí conserva posición y candidato. "
        "El JSON registra `evidence_available=false` para hacerlo explícito."
    )

    lines.extend([
        "",
        "## Criterios señalados con kw2.5",
        "",
        "| Caso | Criterio | Prioridad | Saturación | Gap +/− | AUC | Confirmados | Motivos |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ])
    flagged = [row for row in report["criteria"] if row["config"] == "kw2.5" and row["non_discriminant"]]
    flagged.sort(
        key=lambda row: (
            -row["keyword_saturation_rate"],
            abs(row["components"]["hybrid"]["positive_minus_negative"]),
        )
    )
    for row in flagged:
        hybrid = row["components"]["hybrid"]
        reasons = ", ".join(row["non_discriminant_reasons"])
        lines.append(
            f"| {row['case_id']} | {row['label']} | {row['priority']} | "
            f"{row['keyword_saturation_rate']:.0%} | {hybrid['positive_minus_negative']:+.3f} | "
            f"{hybrid['pairwise_auc']:.3f} | {row['confirmed_rate']:.0%} | {reasons} |"
        )

    lines.extend([
        "",
        "## Comparación kw2.5 − kw1.0 con mayor aumento de saturación",
        "",
        "| Caso | Criterio | Δ saturación | Δ gap híbrido | Δ AUC híbrida |",
        "|---|---|---:|---:|---:|",
    ])
    comparisons = sorted(
        report["comparisons"],
        key=lambda row: -row["kw2.5_minus_kw1.0"]["keyword_saturation_rate"],
    )[:25]
    for row in comparisons:
        delta = row["kw2.5_minus_kw1.0"]
        lines.append(
            f"| {row['case_id']} | {row['label']} | {delta['keyword_saturation_rate']:+.0%} | "
            f"{delta['hybrid_positive_minus_negative']:+.3f} | {delta['hybrid_pairwise_auc']:+.3f} |"
        )
    lines.extend([
        "",
        "## Reproducción",
        "",
        "```powershell",
        "py -3 -m benchmark.audit.criteria_audit benchmark/results/manual_suites/talentclef-20-v1 --output benchmark/audit/reports/talentclef-20-v1",
        "```",
        "",
    ])
    return "\n".join(lines)


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "criteria-audit.json"
    markdown_path = output_dir / "criteria-audit.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path, help="Directory containing paired manual-suite cases")
    parser.add_argument("--output", type=Path, required=True, help="Directory for JSON and Markdown reports")
    args = parser.parse_args()
    report = audit_suite(args.suite)
    json_path, markdown_path = write_report(report, args.output)
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
