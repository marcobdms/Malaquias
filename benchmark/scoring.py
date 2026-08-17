"""Adaptador de benchmark sobre el mismo nucleo matematico que usa la API."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np

from backend.app.scoring_core import (
    aggregate_semantic_score,
    apply_strictness,
    chunk_text,
    hybrid_score,
    keyword_score,
    tokenize,
)


def cosine_scores(query_vector: np.ndarray, candidate_vectors: np.ndarray) -> np.ndarray:
    query = np.asarray(query_vector, dtype=np.float32)
    candidates = np.asarray(candidate_vectors, dtype=np.float32)
    query_norm = np.linalg.norm(query)
    candidate_norms = np.linalg.norm(candidates, axis=1)
    denominator = candidate_norms * query_norm
    dots = candidates @ query
    return np.divide(dots, denominator, out=np.zeros_like(dots), where=denominator != 0)


def _row(
    candidate_id: str,
    candidate_text: str,
    job_text: str,
    semantic: float,
    *,
    balance: float,
    strictness: str,
    keyword_multiplier: float,
) -> dict[str, float | str]:
    keyword = keyword_score(candidate_text, job_text, keyword_multiplier)
    raw = hybrid_score(semantic, keyword, balance)
    return {
        "candidate_id": candidate_id,
        "score": round(raw, 6),
        "display_score": round(apply_strictness(raw, strictness), 6),
        "semantic_score": round(float(semantic), 6),
        "keyword_score": round(keyword, 6),
        "hybrid_score": round(raw, 6),
    }


def rank_pool(
    job_text: str,
    candidate_ids: Iterable[str],
    candidate_texts: Iterable[str],
    job_vector: np.ndarray,
    candidate_vectors: np.ndarray,
    *,
    balance: float,
    strictness: str,
    keyword_multiplier: float,
) -> list[dict[str, float | str]]:
    semantic_scores = cosine_scores(job_vector, candidate_vectors)
    rows = [
        _row(
            candidate_id, candidate_text, job_text, float(semantic),
            balance=balance, strictness=strictness, keyword_multiplier=keyword_multiplier,
        )
        for candidate_id, candidate_text, semantic in zip(
            candidate_ids, candidate_texts, semantic_scores, strict=True
        )
    ]
    return sorted(rows, key=lambda row: (-float(row["score"]), str(row["candidate_id"])))


def rank_pool_chunked(
    job_text: str,
    candidate_ids: Iterable[str],
    candidate_texts: Iterable[str],
    job_vectors: np.ndarray,
    candidate_vectors: Mapping[str, np.ndarray],
    *,
    balance: float,
    strictness: str,
    keyword_multiplier: float,
    semantic_top_k: int,
) -> list[dict[str, float | str]]:
    rows = []
    for candidate_id, candidate_text in zip(candidate_ids, candidate_texts, strict=True):
        semantic = aggregate_semantic_score(
            job_vectors, candidate_vectors[candidate_id], top_k=semantic_top_k
        )
        rows.append(_row(
            candidate_id, candidate_text, job_text, semantic,
            balance=balance, strictness=strictness, keyword_multiplier=keyword_multiplier,
        ))
    return sorted(rows, key=lambda row: (-float(row["score"]), str(row["candidate_id"])))


__all__ = [
    "apply_strictness", "chunk_text", "keyword_score", "rank_pool", "rank_pool_chunked", "tokenize"
]
