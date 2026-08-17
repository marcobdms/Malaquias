"""Create an anonymised, reproducible human-review package from a benchmark run.

The adapter accepts the regular benchmark ``result.json`` (multiple queries) and
the single-case ``engine_result.json`` produced by the visual/API smoke test.
Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


REVIEW_SCHEMA_VERSION = "1.0"
DIRECT_PII_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"(?:https?://|www\.|linkedin\.com/)\S+", re.IGNORECASE),
    re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"),
)
SECTION_MARKERS = (
    "experiencia profesional",
    "experiencia laboral",
    "work experience",
    "professional experience",
    "employment history",
    "habilidades",
    "skills",
    "competencias",
)
EVIDENCE_HEADINGS = (
    "experiencia profesional",
    "experiencia laboral",
    "work experience",
    "professional experience",
    "habilidades técnicas",
    "habilidades",
    "technical skills",
    "skills",
    "competencias",
    "certificaciones profesionales",
    "certificaciones",
    "certifications",
)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Se esperaba un objeto JSON en {path}")
    return value


def _clean_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def redact_direct_pii(text: str, known_name: str | None = None) -> str:
    """Remove direct identifiers while retaining job-relevant prose.

    This is deterministic and intentionally conservative. It is not advertised
    as a general-purpose anonymiser for arbitrary private CVs.
    """

    cleaned = text
    if known_name and known_name.strip():
        cleaned = re.sub(re.escape(known_name.strip()), "[NOMBRE OMITIDO]", cleaned, flags=re.IGNORECASE)
    for pattern in DIRECT_PII_PATTERNS:
        cleaned = pattern.sub("[DATO OMITIDO]", cleaned)
    return cleaned


def _first_section_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        folded = _clean_space(line).casefold()
        if any(marker in folded for marker in SECTION_MARKERS):
            return index
    return None


def professional_evidence(text: str, max_chars: int = 900) -> tuple[str | None, list[str]]:
    """Extract non-header professional evidence and redact direct identifiers."""

    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not raw_lines:
        return None, ["El documento del candidato está vacío."]

    known_name = raw_lines[0]
    start = _first_section_index(raw_lines)
    if start is None:
        return None, ["No se detectó una sección profesional segura; no se incluyó texto bruto."]

    lines = raw_lines[start + 1 :]
    evidence: list[str] = []
    active_heading = ""
    for line in lines:
        folded = _clean_space(line).casefold().rstrip(":")
        if folded in EVIDENCE_HEADINGS:
            active_heading = folded
            continue
        if "@" in line or "linkedin" in folded or "http" in folded or "www." in folded:
            continue

        # Bullets and skill/certification lines carry useful evidence without the
        # CV header. Plain lines are omitted because they often contain employers,
        # locations, dates or other indirect identifiers.
        is_bullet = bool(re.match(r"^[•●▪\-*–—]", line))
        is_skill_line = ":" in line and any(
            marker in active_heading for marker in ("habilidad", "skill", "competencia", "certific")
        )
        if not (is_bullet or is_skill_line):
            continue

        safe = redact_direct_pii(line, known_name=known_name)
        safe = re.sub(r"^[•●▪\-*–—]\s*", "", safe)
        safe = _clean_space(safe)
        if safe and safe not in evidence:
            evidence.append(safe)
        if sum(len(item) + 2 for item in evidence) >= max_chars:
            break

    if not evidence:
        return None, ["No se encontró evidencia profesional que pudiera incluirse sin la cabecera del CV."]

    result = " • ".join(evidence)
    if len(result) > max_chars:
        result = result[: max_chars - 1].rstrip() + "…"
    return result, []


def _analysis_evidence(analysis: dict[str, Any], max_chars: int = 900) -> tuple[str | None, list[str]]:
    chunks: list[str] = []
    for key in ("fortalezas", "carencias"):
        values = analysis.get(key)
        if isinstance(values, list):
            chunks.extend(str(value) for value in values if value)
    if analysis.get("valoracion"):
        chunks.append(str(analysis["valoracion"]))
    known_name = str(analysis.get("nombre_candidato") or "")
    safe = redact_direct_pii(" • ".join(chunks), known_name=known_name)
    safe = _clean_space(safe)
    if not safe:
        return None, ["El análisis no contiene evidencia profesional reutilizable."]
    if len(safe) > max_chars:
        safe = safe[: max_chars - 1].rstrip() + "…"
    return safe, []


def _anonymous_id(run_id: str, query_id: str, candidate_id: str) -> str:
    digest = hashlib.sha256(f"{run_id}:{query_id}:{candidate_id}".encode("utf-8")).hexdigest()[:10]
    return f"C-{digest.upper()}"


def _score_components(candidate: dict[str, Any]) -> dict[str, float]:
    known = (
        "score",
        "ranking_score",
        "match_score",
        "display_score",
        "semantic_score",
        "keyword_score",
        "hybrid_score",
        "required_coverage",
    )
    components: dict[str, float] = {}
    nested = candidate.get("score_components")
    if isinstance(nested, dict):
        for key, value in nested.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                components[str(key)] = round(float(value), 6)
    for key in known:
        value = candidate.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            components[key] = round(float(value), 6)
    return components


def _requirements(candidate: dict[str, Any]) -> dict[str, Any]:
    state = candidate.get("eligibility_state")
    coverage = candidate.get("required_coverage")
    criteria = candidate.get("criteria_scores")
    nested_components = candidate.get("score_components")
    if criteria is None and isinstance(nested_components, dict):
        criteria = nested_components.get("criteria")
    available = state is not None or coverage is not None or isinstance(criteria, (dict, list))
    return {
        "available": available,
        "eligibility_state": state,
        "required_coverage": coverage,
        "criteria_scores": criteria if isinstance(criteria, (dict, list)) else None,
        "note": None if available else "El run no conservó el diagnóstico de requisitos obligatorios.",
    }


def _candidate_timing(candidate: dict[str, Any]) -> dict[str, float]:
    timing: dict[str, float] = {}
    nested = candidate.get("timing")
    if isinstance(nested, dict):
        for key, value in nested.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                timing[str(key)] = round(float(value), 4)
    for key, value in candidate.items():
        if key.endswith(("_ms", "_seconds")) and isinstance(value, (int, float)) and not isinstance(value, bool):
            timing[str(key)] = round(float(value), 4)
    return timing


def _expected_label(candidate: dict[str, Any]) -> int | None:
    value = candidate.get("relevance", candidate.get("expected_relevance"))
    if value is None:
        return None
    try:
        return 1 if float(value) > 0 else 0
    except (TypeError, ValueError):
        return None


def _outcome(expected: int | None, in_top: bool) -> str:
    if expected is None:
        return "sin_etiqueta_esperada"
    if in_top and expected == 1:
        return "acierto_positivo"
    if in_top and expected == 0:
        return "falso_positivo"
    if not in_top and expected == 1:
        return "falso_negativo"
    return "acierto_negativo"


def _resolve_source_root(run: dict[str, Any], override: Path | None) -> Path | None:
    if override:
        return override.resolve()
    raw = (run.get("inputs") or {}).get("source_root")
    if raw:
        path = Path(str(raw))
        if path.exists():
            return path
    return None


def _read_text_if_exists(path: Path | None) -> str | None:
    if not path or not path.is_file():
        return None
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _request_job_description(run: dict[str, Any], run_path: Path) -> str | None:
    raw_request = (run.get("inputs") or {}).get("request")
    if not raw_request:
        return None
    configured = Path(str(raw_request))
    candidates = [configured]
    if not configured.is_absolute():
        candidates.append(run_path.parent / configured)
    if not configured.is_file():
        root = _benchmark_root(run_path)
        if root is not None:
            candidates.extend(sorted(root.rglob(configured.name)))
    for path in candidates:
        if not path.is_file():
            continue
        try:
            request = _read_json(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        description = request.get("job_description")
        if isinstance(description, str) and description.strip():
            return redact_direct_pii(description)
    return None


def _find_source_file(root: Path | None, folder: str, item_id: str) -> Path | None:
    if root is None:
        return None
    directory = root / folder
    exact = directory / item_id
    if exact.is_file():
        return exact
    matches = sorted(directory.glob(f"{item_id}.*")) if directory.is_dir() else []
    return matches[0] if matches else None


def _query_specs(
    run: dict[str, Any], run_path: Path, ground_truth: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    queries = run.get("queries")
    if isinstance(queries, list):
        return [query for query in queries if isinstance(query, dict)]
    ranking = run.get("ranking")
    if isinstance(ranking, list):
        ground_truth = ground_truth or {}
        query_id = str(run.get("query_id") or ground_truth.get("query_id") or run.get("case_id") or "single-case")
        return [{
            "query_id": query_id,
            "ranking": ranking,
            "metrics": run.get("metrics") or {},
            "_offer_path": run_path.parent / "offer.txt",
        }]
    raise ValueError("Formato no compatible: el JSON no contiene 'queries' ni 'ranking'.")


def _selection(ranking: list[dict[str, Any]], top: int, errors: int) -> list[tuple[int, dict[str, Any], str]]:
    selected: list[tuple[int, dict[str, Any], str]] = []
    for index, candidate in enumerate(ranking[:top], start=1):
        selected.append((index, candidate, "top"))
    if errors > 0:
        false_negatives = [
            (index, candidate, "ejemplo_falso_negativo")
            for index, candidate in enumerate(ranking[top:], start=top + 1)
            if _expected_label(candidate) == 1
        ]
        selected.extend(false_negatives[:errors])
    return selected


def _load_case_ground_truth(run_path: Path) -> dict[str, Any]:
    path = run_path.parent / "ground_truth.json"
    if not path.is_file():
        return {}
    try:
        return _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}


def _ground_truth_source_id(candidate: dict[str, Any], ground_truth: dict[str, Any]) -> str | None:
    direct = candidate.get("source_candidate_id")
    if direct is not None:
        return str(direct)
    filename = str(candidate.get("filename") or "")
    internal_id = str(candidate.get("candidate_id") or "")
    for item in ground_truth.get("candidates") or []:
        if not isinstance(item, dict):
            continue
        if filename and str(item.get("filename") or "") == filename:
            value = item.get("candidate_id")
            return str(value) if value is not None else None
        if internal_id and str(item.get("candidate_id") or "") == internal_id:
            return internal_id
    return internal_id if internal_id.isdigit() else None


def _benchmark_root(run_path: Path) -> Path | None:
    for parent in run_path.parents:
        if parent.name.casefold() == "benchmark":
            return parent
    return None


@lru_cache(maxsize=512)
def _find_corpus_source(benchmark_root: Path, source_id: str) -> Path | None:
    data_root = benchmark_root / "data"
    if not data_root.is_dir():
        return None
    matches = sorted(
        path for path in data_root.rglob(source_id)
        if path.is_file() and path.parent.name.casefold() == "corpus"
    )
    if not matches:
        matches = sorted(
            path for path in data_root.rglob(f"{source_id}.*")
            if path.is_file() and path.parent.name.casefold() == "corpus"
        )
    return matches[0] if matches else None


def _extract_case_pdf(path: Path) -> tuple[str | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        from pypdf import PdfReader

        with path.open("rb") as handle:
            text = "\n".join((page.extract_text() or "") for page in PdfReader(handle).pages)
        return text or None, None
    except (ImportError, OSError, ValueError) as exc:
        return None, f"No se pudo extraer el PDF local de forma segura: {type(exc).__name__}."


def _candidate_evidence(
    candidate: dict[str, Any],
    source_root: Path | None,
    candidate_id: str,
    run_path: Path,
    ground_truth: dict[str, Any],
) -> tuple[str | None, str | None, list[str]]:
    source_id = _ground_truth_source_id(candidate, ground_truth) or candidate_id
    source = _find_source_file(source_root, "corpus", source_id)
    if source is None:
        root = _benchmark_root(run_path)
        if root is not None:
            source = _find_corpus_source(root, source_id)
    text = _read_text_if_exists(source)
    if text is not None:
        evidence, warnings = professional_evidence(text)
        return evidence, "talentclef_corpus", warnings

    filename = candidate.get("filename")
    if filename:
        pdf_text, pdf_warning = _extract_case_pdf(run_path.parent / "cvs" / Path(str(filename)).name)
        if pdf_text:
            evidence, warnings = professional_evidence(pdf_text)
            return evidence, "case_pdf", warnings
        if pdf_warning:
            pdf_warnings = [pdf_warning]
        else:
            pdf_warnings = []
    else:
        pdf_warnings = []

    analysis = candidate.get("analysis")
    if isinstance(analysis, dict):
        evidence, warnings = _analysis_evidence(analysis)
        return evidence, "llm_analysis", pdf_warnings + warnings
    return None, None, pdf_warnings + [
        "No se pudo localizar el perfil en el corpus ni extraer el PDF relacionado por ground_truth.json."
    ]


def build_review_package(
    run_path: Path,
    *,
    top: int = 10,
    errors: int = 5,
    query_ids: Iterable[str] | None = None,
    source_root: Path | None = None,
) -> dict[str, Any]:
    """Build the serialisable review package without writing to disk."""

    if top < 1:
        raise ValueError("top debe ser al menos 1")
    if errors < 0:
        raise ValueError("errors no puede ser negativo")

    run_path = run_path.resolve()
    run = _read_json(run_path)
    run_id = str(run.get("run_id") or run.get("case_id") or run_path.parent.name)
    ground_truth = _load_case_ground_truth(run_path)
    request_offer = _request_job_description(run, run_path)
    allowed = {str(value) for value in query_ids} if query_ids else None
    resolved_root = _resolve_source_root(run, source_root)
    warnings: list[str] = []
    if resolved_root is None and isinstance(run.get("queries"), list):
        warnings.append("No se localizó source_root; las ofertas y evidencias de CV pueden quedar vacías.")

    package_queries: list[dict[str, Any]] = []
    requirements_available = False
    for query in _query_specs(run, run_path, ground_truth):
        query_id = str(query.get("query_id") or "unknown")
        if allowed is not None and query_id not in allowed:
            continue
        ranking = [item for item in (query.get("ranking") or []) if isinstance(item, dict)]
        offer_path = query.get("_offer_path") or _find_source_file(resolved_root, "queries", query_id)
        offer_text = _read_text_if_exists(Path(offer_path) if offer_path else None)
        if offer_text is None:
            offer_text = request_offer
        offer_warnings: list[str] = []
        if offer_text is None:
            offer_warnings.append("No se pudo recuperar el texto de la vacante.")
        else:
            offer_text = redact_direct_pii(offer_text)

        review_candidates: list[dict[str, Any]] = []
        for rank, candidate, selection_reason in _selection(ranking, top, errors):
            candidate_id = str(candidate.get("candidate_id") or candidate.get("filename") or f"rank-{rank}")
            expected = _expected_label(candidate)
            requirements = _requirements(candidate)
            requirements_available = requirements_available or bool(requirements["available"])
            evidence, evidence_source, evidence_warnings = _candidate_evidence(
                candidate, resolved_root, candidate_id, run_path, ground_truth
            )
            review_candidates.append({
                "anonymous_id": _anonymous_id(run_id, query_id, candidate_id),
                "rank": int(candidate.get("position") or rank),
                "selection_reason": selection_reason,
                "expected_label": expected,
                "expected_label_meaning": (
                    "relevante según el dataset" if expected == 1 else
                    "no relevante según el dataset" if expected == 0 else
                    "sin etiqueta"
                ),
                "benchmark_outcome_at_cutoff": _outcome(expected, rank <= top),
                "score_components": _score_components(candidate),
                "requirements": requirements,
                "timing": _candidate_timing(candidate),
                "professional_evidence": evidence,
                "evidence_source": evidence_source,
                "warnings": evidence_warnings,
            })

        package_queries.append({
            "query_id": query_id,
            "cutoff": top,
            "pool_size": query.get("pool_size", len(ranking)),
            "relevant_count": query.get("relevant_count"),
            "metrics": query.get("metrics") or {},
            "offer": {"text": offer_text, "warnings": offer_warnings},
            "candidates": review_candidates,
        })

    if allowed is not None:
        found = {query["query_id"] for query in package_queries}
        missing = sorted(allowed - found)
        if missing:
            raise ValueError(f"No se encontraron query_id: {', '.join(missing)}")
    if not package_queries:
        raise ValueError("No hay consultas seleccionadas para revisar.")
    if not requirements_available:
        warnings.append("Este run no conserva estados ni cobertura de requisitos obligatorios.")

    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "purpose": "human_relevance_review",
        "source_run": {
            "run_id": run_id,
            "schema_version": run.get("schema_version"),
            "created_at": run.get("created_at"),
            "task": run.get("task") or "single_case_pipeline",
            "parameters": run.get("parameters") or {},
            "metrics": run.get("metrics") or {},
            "timing": run.get("timing") or {},
        },
        "generation": {
            "top_cutoff": top,
            "false_negative_examples_per_query": errors,
            "query_filter": sorted(allowed) if allowed else None,
            "pii_policy": "Sin nombre, correo, teléfono, URL, cabecera ni identificador original del candidato.",
            "reproducible": True,
        },
        "limitations": warnings,
        "queries": package_queries,
    }


def _fmt_number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value) if value is not None else "—"


def _render_markdown(package: dict[str, Any]) -> str:
    source = package["source_run"]
    lines = [
        f"# Revisión humana — {source['run_id']}",
        "",
        "Este documento permite contrastar el ranking con criterio humano. La etiqueta del dataset no se trata como verdad absoluta: Marco puede confirmarla o corregirla en `review_form.json`.",
        "",
        "Escala humana: **0 = no encaja**, **1 = dudoso / falta evidencia**, **2 = encaja**.",
        "",
        f"- Pipeline: `{source['task']}`",
        f"- Corte evaluado: top {package['generation']['top_cutoff']}",
        f"- Consultas incluidas: {len(package['queries'])}",
        "- Privacidad: candidatos anonimizados; no se incluyen nombres, contacto, URLs, cabeceras ni IDs originales.",
    ]
    if package["limitations"]:
        lines.extend(["", "## Limitaciones detectadas", ""])
        lines.extend(f"- {warning}" for warning in package["limitations"])
    if source.get("timing"):
        timing = ", ".join(
            f"{key}: {_fmt_number(value)}" for key, value in sorted(source["timing"].items())
        )
        lines.extend(["", f"Tiempos del run: {timing}"])

    for query in package["queries"]:
        lines.extend(["", f"## Vacante {query['query_id']}", ""])
        if query["metrics"]:
            metrics = ", ".join(f"{key}: {_fmt_number(value)}" for key, value in sorted(query["metrics"].items()))
            lines.extend([f"Métricas guardadas: {metrics}", ""])
        offer = query["offer"]
        lines.extend(["### Texto de la vacante", "", offer["text"] or "_No disponible._", ""])
        for warning in offer["warnings"]:
            lines.append(f"> Limitación: {warning}")
        lines.extend([
            "",
            "### Candidatos para revisar",
            "",
            "| Puesto | Candidato | Etiqueta esperada | Resultado del motor | Score principal | Requisitos |",
            "|---:|---|---|---|---:|---|",
        ])
        for candidate in query["candidates"]:
            scores = candidate["score_components"]
            main_score = scores.get("ranking_score", scores.get("score", scores.get("match_score")))
            req = candidate["requirements"]
            req_text = req["eligibility_state"] or ("disponible" if req["available"] else "no disponible")
            lines.append(
                f"| {candidate['rank']} | `{candidate['anonymous_id']}` | "
                f"{_fmt_number(candidate['expected_label'])} | {candidate['benchmark_outcome_at_cutoff']} | "
                f"{_fmt_number(main_score)} | {req_text} |"
            )
        for candidate in query["candidates"]:
            lines.extend(["", f"#### {candidate['anonymous_id']} — puesto {candidate['rank']}", ""])
            components = ", ".join(
                f"{key}={_fmt_number(value)}" for key, value in sorted(candidate["score_components"].items())
            ) or "no disponibles"
            timing = ", ".join(
                f"{key}={_fmt_number(value)}" for key, value in sorted(candidate["timing"].items())
            ) or "no disponible"
            requirements = candidate["requirements"]
            requirements_summary = (
                f"estado={requirements['eligibility_state'] or '—'}, "
                f"cobertura={_fmt_number(requirements['required_coverage'])}"
                if requirements["available"] else requirements["note"]
            )
            lines.extend([
                f"- Selección: {candidate['selection_reason']}",
                f"- Etiqueta esperada: {candidate['expected_label_meaning']}",
                f"- Componentes: {components}",
                f"- Requisitos: {requirements_summary}",
                f"- Timing: {timing}",
                f"- Evidencia profesional anonimizada ({candidate['evidence_source'] or 'sin fuente'}): {candidate['professional_evidence'] or 'no disponible'}",
            ])
            criteria = requirements.get("criteria_scores")
            if isinstance(criteria, list):
                lines.append("- Criterios:")
                for criterion in criteria:
                    if not isinstance(criterion, dict):
                        continue
                    lines.append(
                        "  - "
                        f"{criterion.get('label') or criterion.get('id') or 'criterio'}: "
                        f"score={_fmt_number(criterion.get('score'))}, "
                        f"semántico={_fmt_number(criterion.get('semantic_score'))}, "
                        f"keyword={_fmt_number(criterion.get('keyword_score'))}, "
                        f"estado={criterion.get('status') or '—'}, "
                        f"prioridad={criterion.get('priority') or '—'}"
                    )
            lines.extend(f"- Aviso: {warning}" for warning in candidate["warnings"])
            lines.append("- Tu valoración: completa `human_label` y `notes` en `review_form.json`.")
    lines.extend([
        "",
        "## Cómo devolver la revisión",
        "",
        "1. Abre `review_form.json`.",
        "2. Para cada candidato, cambia `human_label: null` por 0, 1 o 2.",
        "3. Añade una razón breve en `notes`, especialmente cuando discrepes de la etiqueta esperada.",
        "4. Comparte el JSON completado; servirá para detectar falsos positivos, falsos negativos y ajustar el motor.",
        "",
    ])
    return "\n".join(lines)


def _review_form(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "source_run_id": package["source_run"]["run_id"],
        "instructions": "Usa 0=no encaja, 1=dudoso/falta evidencia, 2=encaja.",
        "label_scale": {
            "0": "no encaja",
            "1": "dudoso o falta evidencia",
            "2": "encaja",
        },
        "queries": [
            {
                "query_id": query["query_id"],
                "candidates": [
                    {
                        "anonymous_id": candidate["anonymous_id"],
                        "rank": candidate["rank"],
                        "expected_label": candidate["expected_label"],
                        "benchmark_outcome_at_cutoff": candidate["benchmark_outcome_at_cutoff"],
                        "human_label": None,
                        "notes": "",
                    }
                    for candidate in query["candidates"]
                ],
            }
            for query in package["queries"]
        ],
    }


def write_review_package(package: dict[str, Any], output_dir: Path) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / "review_package.json"
    form_path = output_dir / "review_form.json"
    summary_path = output_dir / "review.md"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    form_path.write_text(json.dumps(_review_form(package), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(_render_markdown(package), encoding="utf-8")
    return package_path, form_path, summary_path


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Genera un paquete anonimizado de revisión humana.")
    parser.add_argument("--run", required=True, type=Path, help="Ruta a result.json o engine_result.json")
    parser.add_argument("--output", required=True, type=Path, help="Directorio de salida")
    parser.add_argument("--top", type=int, default=10, help="Corte top-N a revisar (por defecto: 10)")
    parser.add_argument("--errors", type=int, default=5, help="Falsos negativos adicionales por vacante")
    parser.add_argument("--query", action="append", dest="queries", help="query_id; se puede repetir")
    parser.add_argument("--source-root", type=Path, help="Raíz alternativa con carpetas queries/ y corpus/")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        package = build_review_package(
            args.run,
            top=args.top,
            errors=args.errors,
            query_ids=args.queries,
            source_root=args.source_root,
        )
        paths = write_review_package(package, args.output)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print("Paquete de revisión generado:")
    for path in paths:
        print(f"- {path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
