"""Compone etiquetas originales y revisiones trazables.

Un overlay provisional nunca muta el ground truth de origen. Esto permite comparar
el ranking contra el dataset, contra una hipótesis revisada y en modo conservador
(casos provisionales excluidos como ``unknown``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from benchmark.metrics import evaluate_ranking

LABELS = {0, 1, 2, "unknown"}
STATUSES = {"provisional", "confirmed"}


def validate_overlay(overlay: Mapping[str, Any]) -> None:
    if overlay.get("schema_version") != "1.0":
        raise ValueError("schema_version de overlay no soportada")
    if not overlay.get("overlay_id"):
        raise ValueError("overlay_id es obligatorio")

    seen: set[tuple[str, str]] = set()
    for item in overlay.get("judgments", []):
        key = (str(item.get("query_id", "")), str(item.get("candidate_id", "")))
        if not all(key) or key in seen:
            raise ValueError("query_id/candidate_id vacío o duplicado")
        seen.add(key)
        if item.get("label") not in LABELS:
            raise ValueError(f"label inválida para {key}")
        if item.get("status") not in STATUSES:
            raise ValueError(f"status inválido para {key}")
        if not item.get("source") or not item.get("reason"):
            raise ValueError(f"source y reason son obligatorios para {key}")
        confidence = item.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            raise ValueError(f"confidence inválida para {key}")


def apply_overlay(
    original: Mapping[str, int | float | str],
    overlay: Mapping[str, Any],
    query_id: str,
    *,
    mode: str,
) -> dict[str, int | float | str]:
    """Crea una vista de etiquetas sin alterar ``original``.

    ``adjudicated`` usa todas las propuestas. ``unknown_aware`` solo aplica
    revisiones confirmadas y excluye las provisionales del cálculo.
    """

    if mode not in {"adjudicated", "unknown_aware"}:
        raise ValueError("mode debe ser adjudicated o unknown_aware")
    validate_overlay(overlay)
    result = dict(original)
    for item in overlay.get("judgments", []):
        if str(item["query_id"]) != str(query_id):
            continue
        candidate_id = str(item["candidate_id"])
        if candidate_id not in result:
            raise ValueError(f"candidato {candidate_id} no existe en el pool original")
        # Una revisión provisional que conserva la etiqueta original es un caso
        # de regresión del motor, no una duda sobre el gold. Debe seguir
        # evaluándose. Solo excluimos propuestas que cambiarían la etiqueta.
        changes_original = item["label"] != original[candidate_id]
        if mode == "unknown_aware" and item["status"] == "provisional" and changes_original:
            result[candidate_id] = "unknown"
        else:
            result[candidate_id] = item["label"]
    return result


def evaluate_label_views(
    ranking: Iterable[str],
    original: Mapping[str, int | float | str],
    overlay: Mapping[str, Any],
    query_id: str,
    cutoffs: Iterable[int] = (5, 10),
) -> dict[str, dict[str, float]]:
    ordered = list(ranking)
    adjudicated = apply_overlay(original, overlay, query_id, mode="adjudicated")
    unknown_aware = apply_overlay(original, overlay, query_id, mode="unknown_aware")
    return {
        "original": evaluate_ranking(ordered, original, cutoffs),
        "provisional_adjudicated": evaluate_ranking(ordered, adjudicated, cutoffs),
        "unknown_aware": evaluate_ranking(ordered, unknown_aware, cutoffs),
    }
