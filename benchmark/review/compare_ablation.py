"""Build a PII-free human-review package for two ablation variants.

The package is intentionally comparative: it selects candidates whose top-k
membership changes, original-dataset false positives/negatives, and optional
forced regression candidates. Provisional overlays are reported alongside the
published label and never overwrite it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Se esperaba un objeto JSON en {path}")
    return value


def _anonymous_id(case_id: str, query_id: str, candidate_id: str) -> str:
    digest = hashlib.sha256(
        f"{case_id}:{query_id}:{candidate_id}".encode("utf-8")
    ).hexdigest()[:10]
    return f"C-{digest.upper()}"


def _label(candidate: dict[str, Any]) -> int | None:
    value = candidate.get("expected_relevance")
    if value is None:
        value = candidate.get("relevance")
    if value is None:
        return None
    try:
        return 1 if float(value) > 0 else 0
    except (TypeError, ValueError):
        return None


def _position(candidate: dict[str, Any], fallback: int) -> int:
    try:
        return int(candidate.get("position", fallback))
    except (TypeError, ValueError):
        return fallback


def _candidate_key(candidate: dict[str, Any]) -> str:
    value = candidate.get("source_candidate_id", candidate.get("candidate_id"))
    if value is None:
        raise ValueError("Candidato sin identificador interno")
    return str(value)


def _safe_number(value: Any, digits: int = 6) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), digits)
    return None


def _lexical_evidence(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only matcher diagnostics, never source CV text or identifiers."""

    components = candidate.get("score_components")
    criteria = components.get("criteria") if isinstance(components, dict) else None
    if not isinstance(criteria, list):
        return []

    evidence: list[dict[str, Any]] = []
    for criterion in criteria:
        if not isinstance(criterion, dict):
            continue
        lexical = criterion.get("lexical_evidence")
        row: dict[str, Any] = {
            "criterion_id": str(criterion.get("id") or ""),
            "criterion_label": str(criterion.get("label") or ""),
            "priority": criterion.get("priority"),
            "status": criterion.get("status"),
            "semantic_score": _safe_number(criterion.get("semantic_score")),
            "keyword_score": _safe_number(criterion.get("keyword_score")),
        }
        if isinstance(lexical, dict):
            row["lexical"] = {
                "reason": lexical.get("reason"),
                "match_source": lexical.get("match_source"),
                "matched_alternative": lexical.get("matched_alternative"),
                "matched_terms": [str(item) for item in lexical.get("matched_terms", [])],
                "matched_specific_terms": [
                    str(item) for item in lexical.get("matched_specific_terms", [])
                ],
                "matched_anchors": [str(item) for item in lexical.get("matched_anchors", [])],
                "exact": bool(lexical.get("exact", False)),
            }
        else:
            row["lexical"] = None
        evidence.append(row)
    return evidence


def _snapshot(candidate: dict[str, Any], position: int) -> dict[str, Any]:
    return {
        "position": position,
        "ranking_score": _safe_number(candidate.get("ranking_score")),
        "match_score": _safe_number(candidate.get("match_score")),
        "eligibility_state": candidate.get("eligibility_state"),
        "required_coverage": _safe_number(candidate.get("required_coverage")),
        "lexical_evidence": _lexical_evidence(candidate),
    }


def _overlay_index(overlay: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    if not overlay:
        return result
    for judgment in overlay.get("judgments", []):
        if not isinstance(judgment, dict):
            continue
        query_id = str(judgment.get("query_id") or "")
        candidate_id = str(judgment.get("candidate_id") or "")
        if query_id and candidate_id:
            result[(query_id, candidate_id)] = judgment
    return result


def _variant_overview(summary: dict[str, Any], variant_id: str) -> dict[str, Any] | None:
    for variant in summary.get("variants", []):
        if not isinstance(variant, dict) or variant.get("variant_id") != variant_id:
            continue
        return {
            "variant_id": variant_id,
            "macro_metrics_original": (variant.get("macro_metrics_by_view") or {}).get("original"),
            "mean_keyword_saturation_rate": variant.get("mean_keyword_saturation_rate"),
            "criteria_saturated_gte_80pct_total": variant.get(
                "criteria_saturated_gte_80pct_total"
            ),
            "false_eligible_top10_original": (
                variant.get("false_eligible_top10_total_by_view") or {}
            ).get("original"),
            "scoring_timing": variant.get("scoring_timing"),
            "cpu_gate_vs_control": variant.get("cpu_gate_vs_control"),
        }
    return None


def _selection_reasons(
    label: int | None,
    control_position: int,
    challenger_position: int,
    cutoff: int,
    forced: bool,
) -> list[str]:
    reasons: list[str] = []
    control_top = control_position <= cutoff
    challenger_top = challenger_position <= cutoff
    if not control_top and challenger_top:
        reasons.append("entra_top10")
    if control_top and not challenger_top:
        reasons.append("sale_top10")
    if label == 0 and (control_top or challenger_top):
        reasons.append("falso_positivo_original")
    if label == 1 and (not control_top or not challenger_top):
        reasons.append("falso_negativo_original")
    if forced:
        reasons.append("regresion_dirigida")
    return reasons


def build_comparison(
    ablation_dir: Path,
    control_variant: str,
    challenger_variant: str,
    cutoff: int = 10,
    overlay: dict[str, Any] | None = None,
    forced_candidates: Iterable[tuple[str, str]] = (),
) -> dict[str, Any]:
    summary = _read_json(ablation_dir / "summary.json")
    overlay_by_key = _overlay_index(overlay)
    forced = {(str(query), str(candidate)) for query, candidate in forced_candidates}
    cases: list[dict[str, Any]] = []
    totals = {"selected": 0, "enters": 0, "leaves": 0, "original_fp": 0, "original_fn": 0}

    case_root = ablation_dir / "cases"
    for case_dir in sorted(path for path in case_root.iterdir() if path.is_dir()):
        control = _read_json(case_dir / f"{control_variant}.json")
        challenger = _read_json(case_dir / f"{challenger_variant}.json")
        query_id = str(control.get("query_id") or challenger.get("query_id") or "")
        case_id = str(control.get("case_id") or challenger.get("case_id") or case_dir.name)

        def indexed(run: dict[str, Any]) -> dict[str, tuple[dict[str, Any], int]]:
            rows: dict[str, tuple[dict[str, Any], int]] = {}
            for fallback, candidate in enumerate(run.get("ranking", []), start=1):
                if isinstance(candidate, dict):
                    rows[_candidate_key(candidate)] = (candidate, _position(candidate, fallback))
            return rows

        control_rows = indexed(control)
        challenger_rows = indexed(challenger)
        if set(control_rows) != set(challenger_rows):
            raise ValueError(f"Los pools no coinciden en {case_id}")

        candidates: list[dict[str, Any]] = []
        for candidate_id in sorted(control_rows):
            control_candidate, control_position = control_rows[candidate_id]
            challenger_candidate, challenger_position = challenger_rows[candidate_id]
            original_label = _label(control_candidate)
            reasons = _selection_reasons(
                original_label,
                control_position,
                challenger_position,
                cutoff,
                (query_id, candidate_id) in forced,
            )
            if not reasons:
                continue
            judgment = overlay_by_key.get((query_id, candidate_id))
            candidates.append(
                {
                    "anonymous_id": _anonymous_id(
                        case_id,
                        query_id,
                        str(control_candidate.get("candidate_id") or candidate_id),
                    ),
                    "original_dataset_label": original_label,
                    "provisional_overlay": (
                        {
                            "label": judgment.get("label"),
                            "status": judgment.get("status"),
                            "source": judgment.get("source"),
                            "confidence": judgment.get("confidence"),
                            "reason": judgment.get("reason"),
                        }
                        if judgment
                        else None
                    ),
                    "selection_reasons": reasons,
                    "control": _snapshot(control_candidate, control_position),
                    "challenger": _snapshot(challenger_candidate, challenger_position),
                }
            )
            totals["selected"] += 1
            totals["enters"] += int("entra_top10" in reasons)
            totals["leaves"] += int("sale_top10" in reasons)
            totals["original_fp"] += int("falso_positivo_original" in reasons)
            totals["original_fn"] += int("falso_negativo_original" in reasons)

        candidates.sort(
            key=lambda row: (
                min(row["control"]["position"], row["challenger"]["position"]),
                row["anonymous_id"],
            )
        )
        if candidates:
            cases.append(
                {
                    "case_id": case_id,
                    "query_id": query_id,
                    "title": control.get("title") or challenger.get("title"),
                    "control_metrics_original": (control.get("metrics_by_view") or {}).get("original"),
                    "challenger_metrics_original": (challenger.get("metrics_by_view") or {}).get("original"),
                    "candidates": candidates,
                }
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_ablation": {
            "suite_id": summary.get("suite_id"),
            "generated_at": summary.get("generated_at"),
            "path": f"benchmark/results/ablations/{ablation_dir.name}",
        },
        "comparison": {
            "control_variant": control_variant,
            "challenger_variant": challenger_variant,
            "cutoff": cutoff,
            "control_overview": _variant_overview(summary, control_variant),
            "challenger_overview": _variant_overview(summary, challenger_variant),
            "promotion_status": "no_go" if not (
                (_variant_overview(summary, challenger_variant) or {})
                .get("cpu_gate_vs_control", {})
                .get("passes", True)
            ) else "pending_human_review",
        },
        "label_policy": {
            "original_dataset": "Etiqueta publicada por TalentCLEF; en este pool, ausencia en qrels se representa como 0 y no equivale necesariamente a negativo humano confirmado.",
            "provisional_overlay": "Opinión externa provisional; se muestra por separado y NO sustituye el dataset ni constituye gold humano.",
            "human_review": "Marco asigna 0=no encaja, 1=dudoso/falta evidencia, 2=encaja o unknown=no puedo juzgar.",
        },
        "eligibility_note": "La elegibilidad y la cobertura mostradas usan el umbral experimental 0.55 de esta ablación. Sirven para comparar variantes, pero no son una decisión definitiva ni una recomendación de contratación.",
        "privacy": "Sin nombres, contacto, URLs, nombres de fichero ni identificadores originales. La evidencia se limita a diagnósticos léxicos del matcher.",
        "totals": totals,
        "cases": cases,
    }


def _fmt(value: Any) -> str:
    return "—" if value is None else f"{value:.4f}" if isinstance(value, float) else str(value)


def _render_evidence(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["  - No disponible en esta variante."]
    lines: list[str] = []
    for row in rows:
        lexical = row.get("lexical")
        if lexical:
            detail = (
                f"razón={lexical.get('reason') or '—'}, origen={lexical.get('match_source') or '—'}, "
                f"alternativa={lexical.get('matched_alternative') or '—'}, "
                f"términos={', '.join(lexical.get('matched_terms') or []) or '—'}, "
                f"anclas={', '.join(lexical.get('matched_anchors') or []) or '—'}"
            )
        else:
            detail = "el control no conservó trazas léxicas"
        lines.append(
            f"  - {row['criterion_label']} ({row['priority']}): estado={row['status']}, "
            f"sem={_fmt(row['semantic_score'])}, kw={_fmt(row['keyword_score'])}; {detail}."
        )
    return lines


def render_markdown(package: dict[str, Any]) -> str:
    comparison = package["comparison"]
    totals = package["totals"]
    lines = [
        "# Revisión humana comparativa — control vs variante experimental",
        "",
        "Este paquete compara exactamente el mismo pool de CV y la misma oferta. El índice es prioridad de ranking, no probabilidad de contratación.",
        "",
        f"- Control: `{comparison['control_variant']}`",
        f"- Variante: `{comparison['challenger_variant']}`",
        f"- Corte: top {comparison['cutoff']}",
        f"- Estado de promoción: **{comparison['promotion_status']}**.",
        f"- Seleccionados: {totals['selected']} · entran: {totals['enters']} · salen: {totals['leaves']} · falsos positivos originales: {totals['original_fp']} · falsos negativos originales: {totals['original_fn']}",
        "- Privacidad: sin PII ni IDs originales; solo diagnósticos léxicos.",
        f"- Elegibilidad: {package['eligibility_note']}",
        "",
        "## Cómo interpretar las etiquetas",
        "",
        "`original_dataset_label` es la señal publicada por TalentCLEF. Un 0 puede ser simplemente ausencia en qrels, no un negativo humano confirmado. `provisional_overlay` es una opinión externa pendiente y nunca sustituye a la original. Tu respuesta en `review_form.json` usa 0/1/2/unknown.",
        "",
    ]
    challenger_overview = comparison.get("challenger_overview") or {}
    control_overview = comparison.get("control_overview") or {}
    cpu_gate = challenger_overview.get("cpu_gate_vs_control") or {}
    if cpu_gate.get("passes") is False:
        increase = cpu_gate.get("relative_change")
        increase_text = _fmt(increase * 100) + "%" if isinstance(increase, (int, float)) else "—"
        lines.extend(
            [
                f"> La variante mejora el ranking macro, pero no se propone para producción: el coste CPU del scoring aumenta {increase_text} frente al control y supera el límite del 15%. La revisión humana sirve para validar calidad, no para aprobar despliegue.",
                "",
            ]
        )
    else:
        relative_change = cpu_gate.get("relative_change")
        change_text = (
            _fmt(relative_change * 100) + "%"
            if isinstance(relative_change, (int, float))
            else "—"
        )
        lines.extend(
            [
                f"> Rendimiento CPU: pasa el límite del 15% (cambio E2E atribuido: {change_text}). La promoción sigue pendiente de revisión humana y holdout.",
                "",
            ]
        )

    def metric(overview: dict[str, Any], key: str) -> Any:
        return (overview.get("macro_metrics_original") or {}).get(key)

    def e2e(overview: dict[str, Any]) -> Any:
        return (overview.get("scoring_timing") or {}).get(
            "attributed_end_to_end_mean_ms_per_candidate"
        )

    lines.extend(
        [
            "## Resumen macro original",
            "",
            "| Variante | P@5 | P@10 | nDCG@10 | Saturación | Falsos eligible top10 | E2E ms/CV |",
            "|---|---:|---:|---:|---:|---:|---:|",
            f"| Control | {_fmt(metric(control_overview, 'precision@5'))} | {_fmt(metric(control_overview, 'precision@10'))} | {_fmt(metric(control_overview, 'ndcg@10'))} | {_fmt(control_overview.get('mean_keyword_saturation_rate'))} | {_fmt(control_overview.get('false_eligible_top10_original'))} | {_fmt(e2e(control_overview))} |",
            f"| Variante | {_fmt(metric(challenger_overview, 'precision@5'))} | {_fmt(metric(challenger_overview, 'precision@10'))} | {_fmt(metric(challenger_overview, 'ndcg@10'))} | {_fmt(challenger_overview.get('mean_keyword_saturation_rate'))} | {_fmt(challenger_overview.get('false_eligible_top10_original'))} | {_fmt(e2e(challenger_overview))} |",
            "",
        ]
    )
    for case in package["cases"]:
        lines.extend([f"## {case['query_id']} — {case.get('title') or 'Vacante'}", ""])
        lines.extend([
            "| Candidato | Motivo | Dataset | Overlay | Control | Variante | Elegibilidad | Cobertura |",
            "|---|---|---:|---|---:|---:|---|---:|",
        ])
        for candidate in case["candidates"]:
            overlay = candidate.get("provisional_overlay")
            overlay_text = "—" if not overlay else f"{overlay.get('label')} ({overlay.get('status')})"
            control = candidate["control"]
            challenger = candidate["challenger"]
            lines.append(
                f"| `{candidate['anonymous_id']}` | {', '.join(candidate['selection_reasons'])} | "
                f"{_fmt(candidate['original_dataset_label'])} | {overlay_text} | "
                f"#{control['position']} / {_fmt(control['ranking_score'])} | "
                f"#{challenger['position']} / {_fmt(challenger['ranking_score'])} | "
                f"{control['eligibility_state']} → {challenger['eligibility_state']} | "
                f"{_fmt(control['required_coverage'])} → {_fmt(challenger['required_coverage'])} |"
            )
        lines.append("")
        for candidate in case["candidates"]:
            lines.extend([
                f"### {candidate['anonymous_id']}",
                "",
                f"- Motivo: {', '.join(candidate['selection_reasons'])}.",
                f"- Etiqueta original: {_fmt(candidate['original_dataset_label'])}.",
            ])
            overlay = candidate.get("provisional_overlay")
            if overlay:
                lines.append(
                    f"- Overlay provisional ({overlay.get('source')}): {overlay.get('label')} — {overlay.get('reason')}"
                )
            lines.extend([
                f"- Control: puesto {candidate['control']['position']}, score {_fmt(candidate['control']['ranking_score'])}, elegibilidad {candidate['control']['eligibility_state']}, cobertura {_fmt(candidate['control']['required_coverage'])}.",
                f"- Variante: puesto {candidate['challenger']['position']}, score {_fmt(candidate['challenger']['ranking_score'])}, elegibilidad {candidate['challenger']['eligibility_state']}, cobertura {_fmt(candidate['challenger']['required_coverage'])}.",
                "- Evidencia léxica del control:",
                *_render_evidence(candidate["control"]["lexical_evidence"]),
                "- Evidencia léxica de la variante:",
                *_render_evidence(candidate["challenger"]["lexical_evidence"]),
                "- Tu decisión: completa `human_label` y `notes` en `review_form.json`.",
                "",
            ])
    return "\n".join(lines).rstrip() + "\n"


def build_review_form(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source_ablation": package["source_ablation"],
        "comparison": package["comparison"],
        "instructions": "Usa 0=no encaja, 1=dudoso/falta evidencia, 2=encaja, o 'unknown'=no puedo juzgar.",
        "label_scale": {
            "0": "no encaja",
            "1": "dudoso o falta evidencia",
            "2": "encaja",
            "unknown": "no puedo juzgar con esta evidencia",
        },
        "cases": [
            {
                "case_id": case["case_id"],
                "query_id": case["query_id"],
                "candidates": [
                    {
                        "anonymous_id": candidate["anonymous_id"],
                        "selection_reasons": candidate["selection_reasons"],
                        "original_dataset_label": candidate["original_dataset_label"],
                        "provisional_overlay_label": (
                            candidate["provisional_overlay"].get("label")
                            if candidate.get("provisional_overlay")
                            else None
                        ),
                        "human_label": None,
                        "notes": "",
                    }
                    for candidate in case["candidates"]
                ],
            }
            for case in package["cases"]
        ],
    }


def write_package(package: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "comparison_package.json").write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "review.md").write_text(render_markdown(package), encoding="utf-8")
    (output_dir / "review_form.json").write_text(
        json.dumps(build_review_form(package), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ablation-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--control", default="criteria-v1-lexical-v1-kw2p5")
    parser.add_argument("--challenger", default="criteria-v1-lexical-v2")
    parser.add_argument("--cutoff", type=int, default=10)
    parser.add_argument("--overlay", type=Path)
    parser.add_argument(
        "--force",
        action="append",
        default=[],
        metavar="QUERY_ID:CANDIDATE_ID",
        help="Incluye una regresión concreta sin publicar el ID interno.",
    )
    args = parser.parse_args()
    forced: list[tuple[str, str]] = []
    for value in args.force:
        query_id, separator, candidate_id = value.partition(":")
        if not separator or not query_id or not candidate_id:
            parser.error(f"--force inválido: {value!r}")
        forced.append((query_id, candidate_id))
    overlay = _read_json(args.overlay) if args.overlay else None
    package = build_comparison(
        args.ablation_dir,
        args.control,
        args.challenger,
        cutoff=args.cutoff,
        overlay=overlay,
        forced_candidates=forced,
    )
    write_package(package, args.output_dir)
    print(json.dumps({"output_dir": str(args.output_dir), "totals": package["totals"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
