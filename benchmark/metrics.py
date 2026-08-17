"""Metricas puras de information retrieval para pools de candidatos."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping


def _known_relevance(
    ranking: Iterable[str], relevance: Mapping[str, float | int | str]
) -> list[float]:
    """Devuelve relevancias conocidas; las etiquetas ``unknown`` no se evaluan."""

    values: list[float] = []
    for candidate_id in ranking:
        value = relevance.get(candidate_id, 0)
        if value == "unknown":
            continue
        values.append(float(value))
    return values


def precision_at_k(
    ranking: Iterable[str], relevance: Mapping[str, float | int | str], k: int
) -> float:
    if k <= 0:
        raise ValueError("k debe ser mayor que cero")
    values = _known_relevance(ranking, relevance)[:k]
    if not values:
        return 0.0
    return sum(value > 0 for value in values) / len(values)


def recall_at_k(
    ranking: Iterable[str], relevance: Mapping[str, float | int | str], k: int
) -> float:
    if k <= 0:
        raise ValueError("k debe ser mayor que cero")
    total_relevant = sum(
        value != "unknown" and float(value) > 0 for value in relevance.values()
    )
    if not total_relevant:
        return 0.0
    values = _known_relevance(ranking, relevance)[:k]
    return sum(value > 0 for value in values) / total_relevant


def reciprocal_rank(
    ranking: Iterable[str], relevance: Mapping[str, float | int | str]
) -> float:
    for position, value in enumerate(_known_relevance(ranking, relevance), start=1):
        if value > 0:
            return 1.0 / position
    return 0.0


def dcg(values: Iterable[float | int], k: int) -> float:
    if k <= 0:
        raise ValueError("k debe ser mayor que cero")
    return sum(
        (2.0 ** float(value) - 1.0) / math.log2(position + 1)
        for position, value in enumerate(list(values)[:k], start=1)
    )


def ndcg_at_k(
    ranking: Iterable[str], relevance: Mapping[str, float | int | str], k: int
) -> float:
    actual = _known_relevance(ranking, relevance)
    ideal = sorted(
        (float(value) for value in relevance.values() if value != "unknown"),
        reverse=True,
    )
    ideal_dcg = dcg(ideal, k)
    return dcg(actual, k) / ideal_dcg if ideal_dcg else 0.0


def evaluate_ranking(
    ranking: Iterable[str],
    relevance: Mapping[str, float | int | str],
    cutoffs: Iterable[int],
) -> dict[str, float]:
    ordered = list(ranking)
    result = {"mrr": reciprocal_rank(ordered, relevance)}
    for k in sorted(set(cutoffs)):
        result[f"precision@{k}"] = precision_at_k(ordered, relevance, k)
        result[f"recall@{k}"] = recall_at_k(ordered, relevance, k)
        result[f"ndcg@{k}"] = ndcg_at_k(ordered, relevance, k)
    return result


def macro_average(rows: Iterable[Mapping[str, float]]) -> dict[str, float]:
    rows = list(rows)
    if not rows:
        return {}
    keys = sorted(set.intersection(*(set(row) for row in rows)))
    return {key: sum(float(row[key]) for row in rows) / len(rows) for key in keys}
