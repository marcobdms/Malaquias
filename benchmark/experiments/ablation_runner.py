"""Ablación PDF de criterios y matchers léxicos, aislada de producción.

Compara dos catálogos de criterios con los matchers léxicos v1 y v2. El CLI
carga SentenceTransformer de forma diferida; importar este módulo o ejecutar sus
tests puros nunca carga el modelo.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from benchmark.experiments.lexical_v2 import (
    compile_lexical_criterion,
    score_compiled_criteria,
)
from benchmark.metrics import evaluate_ranking, macro_average
from benchmark.provenance import sha256_file
from backend.app.job_criteria import build_scoring_criteria, parse_job_criteria
from backend.app.scoring_core import (
    aggregate_semantic_score,
    apply_strictness,
    hybrid_score,
    keyword_score_any,
    rank_candidate_results,
    required_eligibility,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = REPO_ROOT / "benchmark/results/manual_suites/talentclef-20-v1"
DEFAULT_V1_CATALOG = REPO_ROOT / "benchmark/criteria/talentclef-development-es-v1.json"
DEFAULT_OVERLAY = REPO_ROOT / "benchmark/adjudication/provisional_external_review.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "benchmark/results/ablations"

VARIANT_SPECS = (
    {"id": "criteria-v1-lexical-v1-kw2p5", "criteria": "v1", "lexical": "v1", "multiplier": 2.5, "control": True},
    {"id": "criteria-v1-lexical-v1-kw1", "criteria": "v1", "lexical": "v1", "multiplier": 1.0, "control": False},
    {"id": "criteria-v1-lexical-v2", "criteria": "v1", "lexical": "v2", "multiplier": None, "control": False},
    {"id": "criteria-v2-lexical-v1-kw2p5", "criteria": "v2", "lexical": "v1", "multiplier": 2.5, "control": False},
    {"id": "criteria-v2-lexical-v1-kw1", "criteria": "v2", "lexical": "v1", "multiplier": 1.0, "control": False},
    {"id": "criteria-v2-lexical-v2", "criteria": "v2", "lexical": "v2", "multiplier": None, "control": False},
)


def discover_v2_catalog(explicit: Path | None = None) -> Path:
    if explicit is not None:
        path = explicit.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"No existe el catálogo v2: {path}")
        return path
    candidates = sorted(
        path.resolve()
        for path in (REPO_ROOT / "benchmark/criteria").glob(
            "talentclef-development-es-v2*.json"
        )
        if path.is_file()
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError(
            "No se detectó catálogo v2; indica --criteria-v2 RUTA"
        )
    raise ValueError(
        "Hay varios catálogos v2; indica --criteria-v2 explícitamente: "
        + ", ".join(str(path) for path in candidates)
    )


def load_catalog(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError(f"Catálogo sin jobs válidos: {path}")
    indexed = {str(job["query_id"]): job for job in jobs}
    if len(indexed) != len(jobs):
        raise ValueError(f"query_id duplicado en catálogo: {path}")
    return payload, indexed


def normalize_criteria(raw_criteria: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Usa la normalización productiva y conserva solo metadatos experimentales."""

    normalized = parse_job_criteria(json.dumps(list(raw_criteria), ensure_ascii=False))
    raw_by_id = {str(row.get("id")): row for row in raw_criteria}
    for criterion in normalized:
        source = raw_by_id.get(str(criterion["id"]), {})
        anchors = source.get("anchor_terms") or []
        if isinstance(anchors, list):
            criterion["anchor_terms"] = [str(value).strip() for value in anchors if str(value).strip()]
    return normalized


def compute_semantic_matrix(
    criterion_vectors: Sequence[Any],
    candidate_vectors: Sequence[Any],
    *,
    top_k: int,
) -> list[list[float]]:
    """Calcula una vez la matriz candidato×criterio para tres matchers léxicos."""

    return [
        [
            aggregate_semantic_score(vectors, cv_vectors, top_k=top_k)
            for vectors in criterion_vectors
        ]
        for cv_vectors in candidate_vectors
    ]


def score_variant(
    candidate_texts: Sequence[str],
    scoring_criteria: Sequence[tuple[dict[str, Any], list[str], float]],
    semantic_matrix: Sequence[Sequence[float]],
    *,
    lexical: str,
    keyword_multiplier: float | None,
    balance: float,
    strictness: str,
    required_threshold: float,
) -> list[dict[str, Any]]:
    """Combina semántica cacheada y léxico sin cargar ni invocar el modelo."""

    if lexical not in {"v1", "v2"}:
        raise ValueError("lexical debe ser v1 o v2")
    if lexical == "v1" and (keyword_multiplier is None or keyword_multiplier <= 0):
        raise ValueError("lexical v1 requiere keyword_multiplier positivo")
    if len(candidate_texts) != len(semantic_matrix):
        raise ValueError("candidate_texts y semantic_matrix no coinciden")
    if any(len(row) != len(scoring_criteria) for row in semantic_matrix):
        raise ValueError("semantic_matrix no coincide con los criterios")

    compiled_criteria = (
        [compile_lexical_criterion(criterion) for criterion, _, _ in scoring_criteria]
        if lexical == "v2"
        else []
    )
    rows: list[dict[str, Any]] = []
    for cv_text, semantic_values in zip(candidate_texts, semantic_matrix, strict=True):
        candidate_lexical = (
            score_compiled_criteria(compiled_criteria, cv_text)
            if lexical == "v2"
            else []
        )
        criteria_rows: list[dict[str, Any]] = []
        weighted_total = 0.0
        total_weight = 0.0
        for criterion_index, ((criterion, alternatives, weight), semantic) in enumerate(zip(
            scoring_criteria, semantic_values, strict=True
        )):
            lexical_diagnostic = None
            if lexical == "v1":
                keyword = keyword_score_any(
                    cv_text, alternatives, float(keyword_multiplier)
                )
            else:
                lexical_diagnostic = candidate_lexical[criterion_index]
                keyword = float(lexical_diagnostic["score"])
            raw = hybrid_score(float(semantic), keyword, balance)
            weighted_total += raw * weight
            total_weight += weight
            criteria_rows.append(
                {
                    "id": criterion["id"],
                    "label": criterion["label"],
                    "priority": criterion["priority"],
                    "score": round(raw, 6),
                    "semantic_score": round(float(semantic), 6),
                    "keyword_score": round(keyword, 6),
                    "status": "confirmed" if raw >= required_threshold else "unknown",
                    "lexical_evidence": lexical_diagnostic,
                }
            )

        raw_total = weighted_total / total_weight if total_weight else 0.0
        eligibility, coverage = required_eligibility(criteria_rows, required_threshold)
        rows.append(
            {
                "ranking_score": round(raw_total, 6),
                "display_score": round(apply_strictness(raw_total, strictness), 6),
                "semantic_score": None,
                "keyword_score": None,
                "eligibility_state": eligibility,
                "required_coverage": round(coverage, 6) if coverage is not None else None,
                "criteria_scores": criteria_rows,
            }
        )
    return rows


def label_views(
    original: Mapping[str, int | float | str],
    query_id: str,
    overlay: Mapping[str, Any] | None,
) -> dict[str, dict[str, int | float | str]]:
    views = {"original": dict(original)}
    if overlay is None:
        return views
    from benchmark.adjudication.overlay import apply_overlay

    views["provisional_adjudicated"] = apply_overlay(
        original, overlay, query_id, mode="adjudicated"
    )
    views["unknown_aware"] = apply_overlay(
        original, overlay, query_id, mode="unknown_aware"
    )
    return views


def criterion_saturation(ranking: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    records: dict[str, list[float]] = {}
    labels: dict[str, str] = {}
    for candidate in ranking:
        components = candidate.get("score_components") or {}
        for criterion in components.get("criteria", []) or []:
            criterion_id = str(criterion["id"])
            labels[criterion_id] = str(criterion.get("label", criterion_id))
            records.setdefault(criterion_id, []).append(float(criterion["keyword_score"]))
    rows = []
    for criterion_id, values in records.items():
        rate = sum(value >= 1.0 - 1e-9 for value in values) / len(values)
        rows.append(
            {
                "criterion_id": criterion_id,
                "label": labels[criterion_id],
                "candidate_count": len(values),
                "keyword_saturation_rate": round(rate, 6),
            }
        )
    rows.sort(key=lambda row: (-row["keyword_saturation_rate"], row["criterion_id"]))
    rates = [float(row["keyword_saturation_rate"]) for row in rows]
    return {
        "definition": "fracción de candidatos con keyword_score == 1.0",
        "mean_rate": round(sum(rates) / len(rates), 6) if rates else 0.0,
        "criteria_saturated_gte_80pct": sum(rate >= 0.8 for rate in rates),
        "criteria": rows,
    }


def false_eligible_top10(
    ranking: Sequence[Mapping[str, Any]],
    labels: Mapping[str, int | float | str],
) -> dict[str, Any]:
    false_rows = []
    known = 0
    for candidate in ranking[:10]:
        candidate_id = str(candidate["source_candidate_id"])
        label = labels.get(candidate_id, 0)
        if label == "unknown":
            continue
        known += 1
        if float(label) <= 0 and candidate.get("eligibility_state") == "eligible":
            false_rows.append(
                {
                    "candidate_id": candidate_id,
                    "filename": candidate.get("filename"),
                    "position": candidate.get("position"),
                    "ranking_score": candidate.get("ranking_score"),
                }
            )
    return {
        "definition": "no relevante conocido marcado eligible dentro del top 10",
        "count": len(false_rows),
        "known_candidates_in_top10": known,
        "candidates": false_rows,
    }


def eligibility_rates(ranking: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Cobertura de ``eligible`` separada por la etiqueta original del dataset."""

    positive_count = 0
    negative_count = 0
    positive_eligible = 0
    negative_eligible = 0
    for candidate in ranking:
        is_positive = float(candidate.get("expected_relevance", 0)) > 0
        is_eligible = candidate.get("eligibility_state") == "eligible"
        if is_positive:
            positive_count += 1
            positive_eligible += int(is_eligible)
        else:
            negative_count += 1
            negative_eligible += int(is_eligible)
    return {
        "positive_count": positive_count,
        "positive_eligible_count": positive_eligible,
        "positive_eligible_rate": round(
            positive_eligible / positive_count, 6
        ) if positive_count else 0.0,
        "negative_count": negative_count,
        "negative_eligible_count": negative_eligible,
        "negative_eligible_rate": round(
            negative_eligible / negative_count, 6
        ) if negative_count else 0.0,
    }


def aggregate_eligibility_rates(
    rates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    positive_count = sum(int(row["positive_count"]) for row in rates)
    positive_eligible = sum(int(row["positive_eligible_count"]) for row in rates)
    negative_count = sum(int(row["negative_count"]) for row in rates)
    negative_eligible = sum(int(row["negative_eligible_count"]) for row in rates)
    return {
        "positive_count": positive_count,
        "positive_eligible_count": positive_eligible,
        "positive_eligible_rate": round(
            positive_eligible / positive_count, 6
        ) if positive_count else 0.0,
        "negative_count": negative_count,
        "negative_eligible_count": negative_eligible,
        "negative_eligible_rate": round(
            negative_eligible / negative_count, 6
        ) if negative_count else 0.0,
    }


def evaluate_case_ranking(
    ranking: Sequence[Mapping[str, Any]],
    query_id: str,
    overlay: Mapping[str, Any] | None,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, Any]]]:
    ordered = [str(row["source_candidate_id"]) for row in ranking]
    original = {
        str(row["source_candidate_id"]): row["expected_relevance"] for row in ranking
    }
    views = label_views(original, query_id, overlay)
    metrics = {
        name: evaluate_ranking(ordered, labels, cutoffs=(5, 10, 20))
        for name, labels in views.items()
    }
    false_eligible = {
        name: false_eligible_top10(ranking, labels) for name, labels in views.items()
    }
    return metrics, false_eligible


def _variant_summary(
    spec: Mapping[str, Any], case_reports: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    view_names = sorted(
        set.intersection(*(set(case["metrics_by_view"]) for case in case_reports))
    ) if case_reports else []
    macro = {
        view: macro_average(case["metrics_by_view"][view] for case in case_reports)
        for view in view_names
    }
    saturation_rates = [float(case["saturation"]["mean_rate"]) for case in case_reports]
    false_totals = {
        view: sum(
            int(case["false_eligible_top10_by_view"][view]["count"])
            for case in case_reports
        )
        for view in view_names
    }
    scoring_total = sum(float(case["formula_scoring_seconds"]) for case in case_reports)
    attributed_total = sum(
        float(case["attributed_end_to_end_seconds"]) for case in case_reports
    )
    candidate_count = sum(int(case["candidate_count"]) for case in case_reports)
    eligibility = aggregate_eligibility_rates(
        [case["eligibility_rates"] for case in case_reports]
    )
    return {
        "variant_id": spec["id"],
        "criteria_version": spec["criteria"],
        "lexical_version": spec["lexical"],
        "keyword_multiplier": spec["multiplier"],
        "is_control": bool(spec["control"]),
        "macro_metrics_by_view": macro,
        "mean_keyword_saturation_rate": round(
            sum(saturation_rates) / len(saturation_rates), 6
        ) if saturation_rates else 0.0,
        "criteria_saturated_gte_80pct_total": sum(
            int(case["saturation"]["criteria_saturated_gte_80pct"])
            for case in case_reports
        ),
        "false_eligible_top10_total_by_view": false_totals,
        "eligibility_rates": eligibility,
        "scoring_timing": {
            "formula_total_seconds": round(scoring_total, 6),
            "attributed_end_to_end_total_seconds": round(attributed_total, 6),
            "case_count": len(case_reports),
            "candidate_count": candidate_count,
            "formula_mean_seconds_per_case": round(scoring_total / len(case_reports), 6)
            if case_reports else 0.0,
            "formula_mean_ms_per_candidate": round(scoring_total * 1000 / candidate_count, 6)
            if candidate_count else 0.0,
            "attributed_end_to_end_mean_ms_per_candidate": round(
                attributed_total * 1000 / candidate_count, 6
            ) if candidate_count else 0.0,
        },
        "cases": list(case_reports),
    }


def build_summary(
    suite_manifest: Mapping[str, Any],
    variant_cases: Mapping[str, Sequence[Mapping[str, Any]]],
    catalogs: Mapping[str, Mapping[str, Any]],
    *,
    overlay_path: Path | None,
    timing: Mapping[str, Any],
) -> dict[str, Any]:
    variants = [
        _variant_summary(spec, variant_cases[spec["id"]]) for spec in VARIANT_SPECS
    ]
    control = next(row for row in variants if row["is_control"])
    control_cpu = float(
        control["scoring_timing"]["attributed_end_to_end_mean_ms_per_candidate"]
    )
    for variant in variants:
        current_cpu = float(
            variant["scoring_timing"]["attributed_end_to_end_mean_ms_per_candidate"]
        )
        delta = current_cpu / control_cpu - 1.0 if control_cpu else 0.0
        control_formula = float(
            control["scoring_timing"]["formula_mean_ms_per_candidate"]
        )
        current_formula = float(
            variant["scoring_timing"]["formula_mean_ms_per_candidate"]
        )
        variant["cpu_gate_vs_control"] = {
            "maximum_increase": 0.15,
            "relative_change": round(delta, 6),
            "passes": delta <= 0.15,
            "scope": "latencia CPU local atribuida: parse + embeddings CV + embeddings/semántica de la versión + fórmula",
            "formula_relative_change_diagnostic": round(
                current_formula / control_formula - 1.0 if control_formula else 0.0,
                6,
            ),
        }
    comparisons = []
    for variant in variants:
        if variant is control:
            continue
        deltas = {}
        for view in set(control["macro_metrics_by_view"]) & set(variant["macro_metrics_by_view"]):
            deltas[view] = {
                key: round(
                    float(variant["macro_metrics_by_view"][view][key])
                    - float(control["macro_metrics_by_view"][view][key]),
                    6,
                )
                for key in control["macro_metrics_by_view"][view]
            }
        comparisons.append(
            {
                "control_variant_id": control["variant_id"],
                "experiment_variant_id": variant["variant_id"],
                "metric_deltas_by_view": deltas,
                "keyword_saturation_delta": round(
                    variant["mean_keyword_saturation_rate"]
                    - control["mean_keyword_saturation_rate"],
                    6,
                ),
            }
        )
    return {
        "schema_version": "1.0",
        "task": "criteria_lexical_ablation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite_id": suite_manifest["suite_id"],
        "case_count": len(suite_manifest["cases"]),
        "candidate_count": suite_manifest.get("candidate_count"),
        "pipeline": "PDF -> pypdf -> validate/clean -> MiniLM chunks -> criterio -> canonical ranking",
        "gemini_used": False,
        "definitions": {
            "original": "etiquetas publicadas por TalentCLEF; ausencias se tratan como 0 en este pool",
            "provisional_adjudicated": "hipótesis de revisión externa; NO ES GOLD",
            "unknown_aware": "solo excluye propuestas provisionales que cambian la etiqueta original; NO ES GOLD",
            "score": "prioridad de ranking, no probabilidad de contratación",
        },
        "inputs": {
            "catalogs": catalogs,
            "overlay": str(overlay_path) if overlay_path else None,
        },
        "timing": dict(timing),
        "variants": variants,
        "comparisons": comparisons,
    }


def render_markdown(summary: Mapping[str, Any]) -> str:
    lines = [
        "# Ablación criterios × matcher léxico",
        "",
        f"Suite: **{summary['suite_id']}** · {summary['case_count']} ofertas · "
        f"{summary['candidate_count']} CV · Gemini: **no**",
        "",
        "Las métricas `provisional_adjudicated` y `unknown_aware` proceden de una revisión externa provisional; no son gold humano. `unknown_aware` excluye solo propuestas que cambiarían la etiqueta original.",
        "",
        "| Variante | P@5 original | P@10 original | nDCG@10 original | Positivos eligible | Negativos eligible | Saturación | Criterios >=80% | Falsos eligible top10 | E2E atribuido ms/CV | Fórmula ms/CV | Gate CPU +15% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in summary["variants"]:
        metrics = variant["macro_metrics_by_view"]["original"]
        lines.append(
            f"| {variant['variant_id']} | {metrics['precision@5']:.3f} | "
            f"{metrics['precision@10']:.3f} | {metrics['ndcg@10']:.3f} | "
            f"{variant['eligibility_rates']['positive_eligible_rate']:.1%} | "
            f"{variant['eligibility_rates']['negative_eligible_rate']:.1%} | "
            f"{variant['mean_keyword_saturation_rate']:.1%} | "
            f"{variant['criteria_saturated_gte_80pct_total']} | "
            f"{variant['false_eligible_top10_total_by_view']['original']} | "
            f"{variant['scoring_timing']['attributed_end_to_end_mean_ms_per_candidate']:.3f} | "
            f"{variant['scoring_timing']['formula_mean_ms_per_candidate']:.3f} | "
            f"{'pasa' if variant['cpu_gate_vs_control']['passes'] else 'falla'} "
            f"({variant['cpu_gate_vs_control']['relative_change']:+.1%}) |"
        )
    if "provisional_adjudicated" in summary["variants"][0]["macro_metrics_by_view"]:
        lines.extend(
            [
                "",
                "## Vista provisional, no-gold",
                "",
                "| Variante | P@5 provisional | P@10 provisional | nDCG@10 provisional | P@10 unknown-aware | Falsos eligible provisional |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for variant in summary["variants"]:
            provisional = variant["macro_metrics_by_view"]["provisional_adjudicated"]
            unknown = variant["macro_metrics_by_view"]["unknown_aware"]
            lines.append(
                f"| {variant['variant_id']} | {provisional['precision@5']:.3f} | "
                f"{provisional['precision@10']:.3f} | {provisional['ndcg@10']:.3f} | "
                f"{unknown['precision@10']:.3f} | "
                f"{variant['false_eligible_top10_total_by_view']['provisional_adjudicated']} |"
            )
    lines.extend(
        [
            "",
            "El índice de Malaquías es una prioridad de ranking, no una probabilidad de contratación.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_overlay(path: Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    if path is None or not path.is_file():
        return None, None
    overlay = json.loads(path.read_text(encoding="utf-8"))
    from benchmark.adjudication.overlay import validate_overlay

    validate_overlay(overlay)
    return overlay, path.resolve()


def _parse_case(case_dir: Path, truth: Mapping[str, Any]) -> tuple[list[dict[str, Any]], float]:
    from backend.app.cv_parser import extract_text_from_pdf
    from backend.app.utils import clean_text, validate_pdf_text

    started = perf_counter()
    parsed = []
    for index, metadata in enumerate(truth["candidates"]):
        item_started = perf_counter()
        pdf_path = case_dir / "cvs" / metadata["filename"]
        with pdf_path.open("rb") as handle:
            raw_text = extract_text_from_pdf(handle)
        valid = validate_pdf_text(raw_text)
        parsed.append(
            {
                "candidate_id": f"cv-{index}",
                "filename": metadata["filename"],
                "source_candidate_id": str(metadata.get("candidate_id")),
                "expected_relevance": metadata.get("expected_relevance", 0),
                "clean": clean_text(raw_text) if valid else "",
                "parse_ms": round((perf_counter() - item_started) * 1000, 3),
            }
        )
    return parsed, perf_counter() - started


def run_ablations(
    suite_dir: Path,
    v1_catalog_path: Path,
    v2_catalog_path: Path,
    output_dir: Path,
    *,
    overlay_path: Path | None = DEFAULT_OVERLAY,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    suite_dir = suite_dir.resolve()
    output_dir = output_dir.resolve()
    summary_path = output_dir / "summary.json"
    if summary_path.exists() and not overwrite:
        raise FileExistsError(
            f"Ya existe {summary_path}; usa --overwrite para reemplazar esta ablación"
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = suite_dir / "suite_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    v1_payload, v1_jobs = load_catalog(v1_catalog_path)
    v2_payload, v2_jobs = load_catalog(v2_catalog_path)
    catalog_inputs = {
        "v1": {
            "path": str(v1_catalog_path.resolve()),
            "sha256": sha256_file(v1_catalog_path),
            "criteria_version": v1_payload.get("criteria_version"),
        },
        "v2": {
            "path": str(v2_catalog_path.resolve()),
            "sha256": sha256_file(v2_catalog_path),
            "criteria_version": v2_payload.get("criteria_version"),
        },
    }
    overlay, resolved_overlay = _load_overlay(overlay_path)

    load_started = perf_counter()
    from backend.app import matcher as production_matcher

    if production_matcher.model is None:
        raise RuntimeError("SentenceTransformer no está disponible")
    model_load_seconds = perf_counter() - load_started
    variants: dict[str, list[dict[str, Any]]] = {spec["id"]: [] for spec in VARIANT_SPECS}
    total_started = perf_counter()
    total_parse = 0.0
    total_cv_encode = 0.0
    total_criteria_encode = {"v1": 0.0, "v2": 0.0}

    for case in manifest["cases"]:
        query_id = str(case["query_id"])
        case_dir = suite_dir / case["path"]
        truth = json.loads((case_dir / "ground_truth.json").read_text(encoding="utf-8"))
        request = json.loads((case_dir / "request.json").read_text(encoding="utf-8"))
        parsed, parse_seconds = _parse_case(case_dir, truth)
        total_parse += parse_seconds
        valid_items = [item for item in parsed if item["clean"]]
        texts = [item["clean"] for item in valid_items]

        version_data: dict[str, dict[str, Any]] = {}
        criteria_sources = {"v1": v1_jobs, "v2": v2_jobs}
        cv_encode_started = perf_counter()
        cv_groups = [
            production_matcher.chunk_text(
                text, production_matcher.CHUNK_TOKENS, production_matcher.CHUNK_OVERLAP
            )
            for text in texts
        ]
        candidate_vectors = production_matcher._encode_groups(cv_groups)
        cv_encode_seconds = perf_counter() - cv_encode_started
        total_cv_encode += cv_encode_seconds
        criteria_encode_seconds: dict[str, float] = {}
        for version, jobs in criteria_sources.items():
            version_encode_started = perf_counter()
            if query_id not in jobs:
                raise ValueError(f"Query {query_id} ausente en catálogo {version}")
            normalized = normalize_criteria(jobs[query_id]["criteria"])
            scoring = build_scoring_criteria(normalized)
            criterion_vectors = production_matcher._encode_groups(
                [alternatives for _, alternatives, _ in scoring]
            )
            version_data[version] = {
                "scoring": scoring,
                "semantics": compute_semantic_matrix(
                    criterion_vectors,
                    candidate_vectors,
                    top_k=production_matcher.SEMANTIC_TOP_K,
                ),
            }
            criteria_encode_seconds[version] = perf_counter() - version_encode_started
            total_criteria_encode[version] += criteria_encode_seconds[version]

        for spec in VARIANT_SPECS:
            data = version_data[spec["criteria"]]
            scoring_started = perf_counter()
            scores = score_variant(
                texts,
                data["scoring"],
                data["semantics"],
                lexical=spec["lexical"],
                keyword_multiplier=spec["multiplier"],
                balance=float(request.get("balance", 0.5)),
                strictness=str(request.get("strictness", "normal")),
                required_threshold=production_matcher.REQUIRED_CONFIRM_THRESHOLD,
            )
            scoring_seconds = perf_counter() - scoring_started
            attributed_end_to_end_seconds = (
                parse_seconds
                + cv_encode_seconds
                + criteria_encode_seconds[spec["criteria"]]
                + scoring_seconds
            )
            score_by_filename = {
                item["filename"]: score
                for item, score in zip(valid_items, scores, strict=True)
            }
            results = []
            for item in parsed:
                score = score_by_filename.get(item["filename"])
                public = {key: item[key] for key in (
                    "candidate_id", "filename", "source_candidate_id",
                    "expected_relevance", "parse_ms",
                )}
                if score is None:
                    results.append(
                        {
                            **public,
                            "match_score": 0.0,
                            "ranking_score": 0.0,
                            "eligibility_state": "extraction_failed",
                            "required_coverage": None,
                            "score_components": None,
                        }
                    )
                else:
                    results.append(
                        {
                            **public,
                            "match_score": round(float(score["display_score"]) * 100, 2),
                            "ranking_score": score["ranking_score"],
                            "eligibility_state": score["eligibility_state"],
                            "required_coverage": score["required_coverage"],
                            "score_components": {
                                "semantic_score": None,
                                "keyword_score": None,
                                "criteria": score["criteria_scores"],
                            },
                        }
                    )
            ranked = [
                dict(row, position=position)
                for position, row in enumerate(rank_candidate_results(results), start=1)
            ]
            metrics, false_eligible = evaluate_case_ranking(ranked, query_id, overlay)
            saturation = criterion_saturation(ranked)
            eligible_rates = eligibility_rates(ranked)
            relative = Path("cases") / case["case_id"] / f"{spec['id']}.json"
            target = output_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            case_result = {
                "schema_version": "1.0",
                "case_id": case["case_id"],
                "query_id": query_id,
                "title": case["title"],
                "variant_id": spec["id"],
                "criteria_version": spec["criteria"],
                "lexical_version": spec["lexical"],
                "keyword_multiplier": spec["multiplier"],
                "formula_scoring_seconds": round(scoring_seconds, 6),
                "attributed_end_to_end_seconds": round(
                    attributed_end_to_end_seconds, 6
                ),
                "candidate_count": len(ranked),
                "timing_breakdown": {
                    "parse_seconds": round(parse_seconds, 6),
                    "cv_embedding_seconds": round(cv_encode_seconds, 6),
                    "criteria_embedding_and_semantic_seconds": round(
                        criteria_encode_seconds[spec["criteria"]], 6
                    ),
                    "formula_scoring_seconds": round(scoring_seconds, 6),
                },
                "metrics_by_view": metrics,
                "saturation": saturation,
                "false_eligible_top10_by_view": false_eligible,
                "eligibility_rates": eligible_rates,
                "ranking": ranked,
            }
            target.write_text(
                json.dumps(case_result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            variants[spec["id"]].append(
                {
                    "case_id": case["case_id"],
                    "query_id": query_id,
                    "title": case["title"],
                    "formula_scoring_seconds": round(scoring_seconds, 6),
                    "attributed_end_to_end_seconds": round(
                        attributed_end_to_end_seconds, 6
                    ),
                    "candidate_count": len(ranked),
                    "metrics_by_view": metrics,
                    "saturation": saturation,
                    "false_eligible_top10_by_view": false_eligible,
                    "eligibility_rates": eligible_rates,
                    "result_path": relative.as_posix(),
                }
            )

    timing = {
        "model_load_seconds": round(model_load_seconds, 4),
        "parse_seconds_total": round(total_parse, 4),
        "cv_embedding_seconds_total": round(total_cv_encode, 4),
        "criteria_embedding_and_semantic_seconds_by_version": {
            version: round(seconds, 4)
            for version, seconds in total_criteria_encode.items()
        },
        "total_wall_seconds": round(perf_counter() - total_started, 4),
        "embedding_reuse": "CV una vez por caso; criterios una vez por caso/versión; tres matchers comparten semántica",
    }
    summary = build_summary(
        manifest,
        variants,
        catalog_inputs,
        overlay_path=resolved_overlay,
        timing=timing,
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path = output_dir / "summary.md"
    markdown_path.write_text(render_markdown(summary), encoding="utf-8")
    return summary_path, markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--criteria-v1", type=Path, default=DEFAULT_V1_CATALOG)
    parser.add_argument("--criteria-v2", type=Path)
    parser.add_argument(
        "--overlay", type=Path, default=DEFAULT_OVERLAY,
        help="Overlay provisional opcional; si no existe solo se informa original.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=DEFAULT_OUTPUT_ROOT / "talentclef-20-v1-criteria-lexical-v2",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    v2_path = discover_v2_catalog(args.criteria_v2)
    json_path, markdown_path = run_ablations(
        args.suite,
        args.criteria_v1,
        v2_path,
        args.output,
        overlay_path=args.overlay,
        overwrite=args.overwrite,
    )
    summary = json.loads(json_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "summary": str(json_path),
                "markdown": str(markdown_path),
                "timing": summary["timing"],
                "variants": [
                    {
                        "variant_id": row["variant_id"],
                        "original": row["macro_metrics_by_view"]["original"],
                        "saturation": row["mean_keyword_saturation_rate"],
                        "false_eligible_top10": row[
                            "false_eligible_top10_total_by_view"
                        ]["original"],
                        "attributed_end_to_end_ms_per_candidate": row["scoring_timing"][
                            "attributed_end_to_end_mean_ms_per_candidate"
                        ],
                        "formula_ms_per_candidate": row["scoring_timing"][
                            "formula_mean_ms_per_candidate"
                        ],
                        "cpu_gate_vs_control": row["cpu_gate_vs_control"],
                    }
                    for row in summary["variants"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
