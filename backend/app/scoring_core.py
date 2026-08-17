"""Nucleo matematico puro compartido por la API y los benchmarks.

No carga modelos ni llama a servicios externos. Recibe embeddings ya calculados
y conserva los componentes del score para que cada run sea auditable.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np


DEFAULT_STOPWORDS = {
    "de", "la", "el", "en", "y", "a", "que", "con", "por", "para",
    "los", "las", "un", "una", "es", "se", "del", "al", "lo", "su",
    "sus", "si", "no", "yo", "mi",
}


def tokenize(text: str, stopwords: set[str] | None = None) -> list[str]:
    ignored = DEFAULT_STOPWORDS if stopwords is None else stopwords
    tokens = re.findall(r"\b\w+\b", text.lower(), flags=re.UNICODE)
    return [token for token in tokens if token not in ignored and len(token) > 2]


def chunk_text(text: str, max_tokens: int = 96, overlap: int = 24) -> list[str]:
    """Divide texto para que MiniLM no descarte el final del CV (limite 128)."""

    if max_tokens < 16:
        raise ValueError("max_tokens debe ser al menos 16")
    if overlap < 0 or overlap >= max_tokens:
        raise ValueError("overlap debe estar entre 0 y max_tokens - 1")
    words = re.findall(r"\S+", text.strip(), flags=re.UNICODE)
    if not words:
        return [""]
    step = max_tokens - overlap
    return [" ".join(words[start:start + max_tokens]) for start in range(0, len(words), step)]


def keyword_score(candidate_text: str, query_text: str, multiplier: float = 2.5) -> float:
    candidate_tokens = set(tokenize(candidate_text))
    query_tokens = set(tokenize(query_text))
    if not query_tokens:
        return 0.0
    return min(1.0, len(candidate_tokens & query_tokens) / len(query_tokens) * multiplier)


def keyword_score_any(candidate_text: str, alternatives: Iterable[str], multiplier: float = 2.5) -> float:
    """Las equivalencias son alternativas OR, no terminos acumulativos."""

    return max((keyword_score(candidate_text, text, multiplier) for text in alternatives), default=0.0)


def cosine_matrix(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    left_matrix = np.atleast_2d(np.asarray(left, dtype=np.float32))
    right_matrix = np.atleast_2d(np.asarray(right, dtype=np.float32))
    left_norms = np.linalg.norm(left_matrix, axis=1, keepdims=True)
    right_norms = np.linalg.norm(right_matrix, axis=1, keepdims=True)
    denominator = left_norms * right_norms.T
    dots = left_matrix @ right_matrix.T
    return np.divide(dots, denominator, out=np.zeros_like(dots), where=denominator != 0)


def aggregate_semantic_score(
    query_vectors: np.ndarray,
    candidate_vectors: np.ndarray,
    *,
    top_k: int = 2,
) -> float:
    """Promedia los mejores fragmentos para evitar matches por una frase aislada."""

    similarities = cosine_matrix(candidate_vectors, query_vectors)
    best_per_candidate_chunk = similarities.max(axis=1)
    count = min(max(1, top_k), len(best_per_candidate_chunk))
    best = np.partition(best_per_candidate_chunk, -count)[-count:]
    return float(np.mean(best))


def hybrid_score(semantic: float, keyword: float, balance: float) -> float:
    if not 0.0 <= balance <= 1.0:
        raise ValueError("balance debe estar entre 0 y 1")
    return balance * keyword + (1.0 - balance) * semantic


def required_eligibility(
    criterion_scores: Iterable[dict[str, object]], threshold: float
) -> tuple[str, float | None]:
    required = [row for row in criterion_scores if row.get("priority") == "required"]
    if not required:
        return "eligible", None
    confirmed = sum(float(row.get("score", 0.0)) >= threshold for row in required)
    coverage = confirmed / len(required)
    return ("eligible" if confirmed == len(required) else "needs_review"), coverage


ELIGIBILITY_ORDER = {
    "eligible": 2,
    "needs_review": 1,
    "extraction_failed": 0,
    "pending": 0,
}


def candidate_sort_key(candidate: dict[str, object]) -> tuple[float, float, float]:
    """Orden canónico compartido por la API y los runners de paridad."""

    coverage = candidate.get("required_coverage")
    return (
        float(ELIGIBILITY_ORDER.get(str(candidate.get("eligibility_state")), 0)),
        float(coverage) if coverage is not None else 1.0,
        float(candidate.get("ranking_score", 0.0)),
    )


def rank_candidate_results(candidates: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(candidates, key=candidate_sort_key, reverse=True)


def apply_strictness(score: float, strictness: str) -> float:
    """Compatibilidad de presentacion; no debe usarse para elegir el ranking."""

    if strictness == "estricto":
        adjusted = (score - 0.4) / 0.6
    elif strictness == "normal":
        adjusted = (score - 0.2) / 0.8
    elif strictness == "flexible":
        adjusted = score
    else:
        raise ValueError(f"strictness desconocido: {strictness}")
    return round(max(0.0, min(1.0, adjusted)), 12)
