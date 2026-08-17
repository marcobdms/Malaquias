"""Create a compact human shortlist from an exhaustive ablation comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from benchmark.review.compare_ablation import _read_json, _render_evidence, _fmt


LABEL_SCALE = {
    "0": "No encaja: el CV no demuestra lo esencial para esta vacante.",
    "1": "Dudoso: podría encajar, pero falta evidencia o hay una diferencia importante de función/nivel.",
    "2": "Sí encaja: el CV demuestra suficientemente lo esencial para esta vacante.",
    "unknown": "No puedo decidir con la información mostrada.",
}


def _professional_evidence_index(review_packages: Iterable[dict[str, Any]]) -> dict[str, str]:
    index: dict[str, str] = {}
    for package in review_packages:
        for query in package.get("queries", []):
            if not isinstance(query, dict):
                continue
            for candidate in query.get("candidates", []):
                if not isinstance(candidate, dict):
                    continue
                anonymous_id = str(candidate.get("anonymous_id") or "")
                evidence = candidate.get("professional_evidence")
                if anonymous_id and isinstance(evidence, str) and evidence.strip():
                    index[anonymous_id] = evidence.strip()
    return index


def _priority(
    query_id: str, candidate: dict[str, Any], has_professional_evidence: bool
) -> tuple[int, int, int, str]:
    reasons = set(candidate.get("selection_reasons") or [])
    control_position = int(candidate["control"]["position"])
    label = candidate.get("original_dataset_label")
    overlay = candidate.get("provisional_overlay")
    if "regresion_dirigida" in reasons:
        tier = 0
    elif overlay is not None:
        tier = 1
    elif query_id == "96027" and label == 0 and control_position <= 10:
        tier = 2
    elif "entra_top10" in reasons or "sale_top10" in reasons:
        tier = 3
    else:
        tier = 4
    if not has_professional_evidence and tier >= 3:
        tier = 5
    return tier, 0 if has_professional_evidence else 1, control_position, str(
        candidate.get("anonymous_id")
    )


def build_shortlist(
    comparison: dict[str, Any],
    evidence_packages: Iterable[dict[str, Any]],
    maximum: int = 16,
    focus_queries: tuple[str, ...] = ("96027", "91821"),
) -> dict[str, Any]:
    evidence_index = _professional_evidence_index(evidence_packages)
    candidates_by_query: dict[str, list[tuple[str | None, dict[str, Any]]]] = {
        query_id: [] for query_id in focus_queries
    }
    for case in comparison.get("cases", []):
        query_id = str(case.get("query_id") or "")
        if query_id not in focus_queries:
            continue
        for candidate in case.get("candidates", []):
            candidates_by_query[query_id].append((case.get("title"), candidate))

    selected: list[tuple[str, str | None, dict[str, Any]]] = []
    base_quota, remainder = divmod(maximum, len(focus_queries))
    for index, query_id in enumerate(focus_queries):
        quota = base_quota + int(index < remainder)
        rows = candidates_by_query[query_id]
        rows.sort(
            key=lambda item: _priority(
                query_id,
                item[1],
                item[1].get("anonymous_id") in evidence_index,
            )
        )
        selected.extend((query_id, title, candidate) for title, candidate in rows[:quota])
    grouped: list[dict[str, Any]] = []
    for query_id in focus_queries:
        rows = []
        title = None
        for selected_query, selected_title, candidate in selected:
            if selected_query != query_id:
                continue
            title = selected_title
            row = dict(candidate)
            row["professional_evidence"] = evidence_index.get(row["anonymous_id"])
            row["evidence_warning"] = (
                None
                if row["professional_evidence"]
                else "No se encontró extracto profesional anonimizado en el paquete previo."
            )
            rows.append(row)
        if rows:
            grouped.append({"query_id": query_id, "title": title, "candidates": rows})

    return {
        "schema_version": "1.0",
        "source_ablation": comparison.get("source_ablation"),
        "comparison": comparison.get("comparison"),
        "label_policy": comparison.get("label_policy"),
        "eligibility_note": comparison.get("eligibility_note"),
        "privacy": "Sin nombres, contacto, URLs, nombres de fichero ni IDs originales. Los extractos proceden del paquete anonimizado ya validado.",
        "selection_policy": "Prioridad: regresiones dirigidas; overlays provisionales; negativos originales por encima del caso positivo dirigido en 96027; movimientos de top10; otros errores originales.",
        "label_scale": LABEL_SCALE,
        "candidate_count": sum(len(case["candidates"]) for case in grouped),
        "cases": grouped,
    }


def render_shortlist(shortlist: dict[str, Any]) -> str:
    comparison = shortlist["comparison"]
    lines = [
        "# Lista corta para revisión humana",
        "",
        "Objetivo: decidir si la variante mejora de verdad el orden, sin asumir que el dataset siempre tiene razón. Revisa primero estos casos; el paquete exhaustivo queda como anexo.",
        "",
        f"- Control: `{comparison['control_variant']}`",
        f"- Variante: `{comparison['challenger_variant']}`",
        f"- Casos: {shortlist['candidate_count']}",
        "- Privacidad: no contiene nombres, contacto, ficheros ni IDs originales.",
        f"- Elegibilidad: {shortlist.get('eligibility_note') or 'experimental; no es una decisión definitiva.'}",
        "",
        "## Qué debes responder",
        "",
        f"- **0** — {LABEL_SCALE['0']}",
        f"- **1** — {LABEL_SCALE['1']}",
        f"- **2** — {LABEL_SCALE['2']}",
        f"- **unknown** — {LABEL_SCALE['unknown']}",
        "",
        "La etiqueta original de TalentCLEF se conserva separada. Un `0` original puede ser una ausencia en qrels, no un rechazo humano confirmado. El overlay es solo una opinión externa provisional.",
        "",
    ]
    for case in shortlist["cases"]:
        lines.extend([f"## {case['query_id']} — {case.get('title') or 'Vacante'}", ""])
        for candidate in case["candidates"]:
            control = candidate["control"]
            challenger = candidate["challenger"]
            overlay = candidate.get("provisional_overlay")
            lines.extend(
                [
                    f"### {candidate['anonymous_id']}",
                    "",
                    f"- Por qué se revisa: {', '.join(candidate['selection_reasons'])}.",
                    f"- Dataset original: {candidate.get('original_dataset_label')}.",
                ]
            )
            if overlay:
                lines.append(
                    f"- Overlay provisional ({overlay.get('source')}): {overlay.get('label')} — {overlay.get('reason')}"
                )
            lines.extend(
                [
                    f"- Control: puesto {control['position']}, score {_fmt(control['ranking_score'])}, {control['eligibility_state']}, cobertura {_fmt(control['required_coverage'])}.",
                    f"- Variante: puesto {challenger['position']}, score {_fmt(challenger['ranking_score'])}, {challenger['eligibility_state']}, cobertura {_fmt(challenger['required_coverage'])}.",
                    f"- Extracto profesional anonimizado: {candidate.get('professional_evidence') or candidate.get('evidence_warning')}",
                    "- Por qué coincidió léxicamente en la variante:",
                    *_render_evidence(challenger.get("lexical_evidence") or []),
                    "- Tu respuesta: escribe `human_label` (0, 1, 2 o unknown) y una nota breve en `review_shortlist_form.json`.",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def build_form(shortlist: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "source_ablation": shortlist.get("source_ablation"),
        "comparison": shortlist.get("comparison"),
        "instructions": "Para cada candidato usa 0, 1, 2 o 'unknown' según la escala. Añade una frase en notes si puedes.",
        "label_scale": LABEL_SCALE,
        "cases": [
            {
                "query_id": case["query_id"],
                "title": case.get("title"),
                "candidates": [
                    {
                        "anonymous_id": candidate["anonymous_id"],
                        "selection_reasons": candidate["selection_reasons"],
                        "original_dataset_label": candidate.get("original_dataset_label"),
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
            for case in shortlist["cases"]
        ],
    }


def write_shortlist(shortlist: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "shortlist_package.json").write_text(
        json.dumps(shortlist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "review_shortlist.md").write_text(
        render_shortlist(shortlist), encoding="utf-8"
    )
    (output_dir / "review_shortlist_form.json").write_text(
        json.dumps(build_form(shortlist), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", required=True, type=Path)
    parser.add_argument("--evidence-package", action="append", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--maximum", type=int, default=16)
    args = parser.parse_args()
    comparison = _read_json(args.comparison)
    evidence_packages = [_read_json(path) for path in args.evidence_package]
    shortlist = build_shortlist(comparison, evidence_packages, maximum=args.maximum)
    write_shortlist(shortlist, args.output_dir)
    print(json.dumps({"candidate_count": shortlist["candidate_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
