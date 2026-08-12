"""Normaliza criterios confirmados y crea entradas claras para el motor actual."""

from __future__ import annotations

import json
from typing import Any


PRIORITIES = {"required", "important", "preferred", "not_evaluable"}
PRIORITY_LABELS = {
    "required": "OBLIGATORIO",
    "important": "IMPORTANTE",
    "preferred": "DESEABLE",
    "not_evaluable": "NO EVALUABLE EN CV",
}
PRIORITY_WEIGHTS = {"required": 3.0, "important": 2.0, "preferred": 1.0}


def parse_job_criteria(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("criteria_json debe ser JSON válido") from exc

    if not isinstance(payload, list):
        raise ValueError("criteria_json debe contener una lista")
    if len(payload) > 30:
        raise ValueError("criteria_json admite un máximo de 30 criterios")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"el criterio {index + 1} debe ser un objeto")

        label = str(item.get("label", "")).strip()
        priority = str(item.get("priority", "important")).strip()
        if not label:
            continue
        if priority not in PRIORITIES:
            raise ValueError(f"prioridad no admitida en el criterio {index + 1}")

        equivalences = item.get("equivalences", [])
        if not isinstance(equivalences, list):
            equivalences = []

        normalized.append(
            {
                "id": str(item.get("id") or f"criterion-{index + 1}"),
                "label": label,
                "priority": priority,
                "evaluable_in_cv": priority != "not_evaluable",
                "equivalences": [str(value).strip() for value in equivalences if str(value).strip()],
            }
        )
    return normalized


def build_scoring_criteria(
    criteria: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], str, float]]:
    weighted: list[tuple[dict[str, Any], str, float]] = []
    for criterion in criteria:
        if not criterion["evaluable_in_cv"]:
            continue
        aliases = criterion.get("equivalences") or []
        text = ". ".join([criterion["label"], *aliases])
        weighted.append((criterion, text, PRIORITY_WEIGHTS[criterion["priority"]]))
    return weighted


def build_job_descriptions(
    original_description: str, criteria: list[dict[str, Any]]
) -> tuple[str, str]:
    """Devuelve una entrada para scoring y otra, contextual, para explicación."""

    if not criteria:
        return original_description, original_description

    evaluable_lines: list[str] = []
    non_evaluable_lines: list[str] = []
    for criterion in criteria:
        aliases = criterion.get("equivalences") or []
        alias_text = f" (equivalencias: {', '.join(aliases)})" if aliases else ""
        line = f"- [{PRIORITY_LABELS[criterion['priority']]}] {criterion['label']}{alias_text}"
        if criterion["evaluable_in_cv"]:
            evaluable_lines.append(line)
        else:
            non_evaluable_lines.append(line)

    matching_description = "\n".join(evaluable_lines) or original_description
    explanation_parts = [
        original_description,
        "\nCRITERIOS CONFIRMADOS PARA ESTA EVALUACIÓN:",
        *(evaluable_lines or ["- No se confirmaron criterios evaluables."]),
    ]
    if non_evaluable_lines:
        explanation_parts.extend(
            [
                "\nASPECTOS RESERVADOS PARA ENTREVISTA (no inferir ni penalizar desde el CV):",
                *non_evaluable_lines,
            ]
        )
    return matching_description, "\n".join(explanation_parts)
