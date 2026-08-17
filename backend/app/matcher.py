"""Scoring local de CVs. Gemini no participa en ningun calculo."""

from __future__ import annotations

from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from .scoring_core import (
    aggregate_semantic_score,
    apply_strictness,
    chunk_text,
    hybrid_score,
    keyword_score,
    keyword_score_any,
    required_eligibility,
)


MODEL_ID = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_TOKENS = 96
CHUNK_OVERLAP = 24
SEMANTIC_TOP_K = 2
REQUIRED_CONFIRM_THRESHOLD = 0.55

print("Cargando modelo SentenceTransformer...")
try:
    model = SentenceTransformer(MODEL_ID)
except Exception as error:
    print(f"Error cargando modelo: {error}")
    model = None


def _encode_groups(text_groups: list[list[str]]) -> list[np.ndarray]:
    if model is None:
        return [np.zeros((len(group), 1), dtype=np.float32) for group in text_groups]
    flat = [text for group in text_groups for text in group]
    vectors = model.encode(flat, convert_to_numpy=True, show_progress_bar=False)
    groups: list[np.ndarray] = []
    offset = 0
    for group in text_groups:
        groups.append(np.asarray(vectors[offset:offset + len(group)], dtype=np.float32))
        offset += len(group)
    return groups


def score_cvs_to_job(
    cv_texts: list[str],
    job_description: str,
    *,
    strictness: str = "normal",
    balance: float = 0.5,
    keyword_multiplier: float = 2.5,
) -> list[dict[str, Any]]:
    if model is None or not cv_texts:
        return []
    groups = [chunk_text(job_description, CHUNK_TOKENS, CHUNK_OVERLAP)] + [
        chunk_text(text, CHUNK_TOKENS, CHUNK_OVERLAP) for text in cv_texts
    ]
    encoded = _encode_groups(groups)
    job_vectors, candidate_vectors = encoded[0], encoded[1:]
    rows = []
    for cv_text, vectors in zip(cv_texts, candidate_vectors, strict=True):
        semantic = aggregate_semantic_score(job_vectors, vectors, top_k=SEMANTIC_TOP_K)
        keyword = keyword_score(cv_text, job_description, keyword_multiplier)
        raw = hybrid_score(semantic, keyword, balance)
        rows.append({
            "ranking_score": round(raw, 6),
            "display_score": round(apply_strictness(raw, strictness), 6),
            "semantic_score": round(semantic, 6),
            "keyword_score": round(keyword, 6),
            "eligibility_state": "eligible",
            "required_coverage": None,
            "criteria_scores": [],
        })
    return rows


def score_cvs_to_criteria(
    cv_texts: list[str],
    scoring_criteria: list[tuple[dict[str, Any], list[str], float]],
    *,
    strictness: str = "normal",
    balance: float = 0.5,
    keyword_multiplier: float = 2.5,
) -> list[dict[str, Any]]:
    if model is None or not cv_texts or not scoring_criteria:
        return []

    alternative_groups = [alternatives for _, alternatives, _ in scoring_criteria]
    cv_groups = [chunk_text(text, CHUNK_TOKENS, CHUNK_OVERLAP) for text in cv_texts]
    encoded = _encode_groups(alternative_groups + cv_groups)
    criterion_vectors = encoded[:len(scoring_criteria)]
    candidate_vectors = encoded[len(scoring_criteria):]

    rows = []
    for cv_text, cv_vectors in zip(cv_texts, candidate_vectors, strict=True):
        criterion_rows = []
        weighted_total = 0.0
        total_weight = 0.0
        for (criterion, alternatives, weight), vectors in zip(
            scoring_criteria, criterion_vectors, strict=True
        ):
            semantic = aggregate_semantic_score(vectors, cv_vectors, top_k=SEMANTIC_TOP_K)
            keyword = keyword_score_any(cv_text, alternatives, keyword_multiplier)
            raw = hybrid_score(semantic, keyword, balance)
            weighted_total += raw * weight
            total_weight += weight
            criterion_rows.append({
                "id": criterion["id"],
                "label": criterion["label"],
                "priority": criterion["priority"],
                "score": round(raw, 6),
                "semantic_score": round(semantic, 6),
                "keyword_score": round(keyword, 6),
                "status": "confirmed" if raw >= REQUIRED_CONFIRM_THRESHOLD else "unknown",
            })

        raw_total = weighted_total / total_weight if total_weight else 0.0
        eligibility, required_coverage = required_eligibility(
            criterion_rows, REQUIRED_CONFIRM_THRESHOLD
        )
        rows.append({
            "ranking_score": round(raw_total, 6),
            "display_score": round(apply_strictness(raw_total, strictness), 6),
            "semantic_score": None,
            "keyword_score": None,
            "eligibility_state": eligibility,
            "required_coverage": round(required_coverage, 6) if required_coverage is not None else None,
            "criteria_scores": criterion_rows,
        })
    return rows


def compare_cvs_to_job(
    cv_texts: list[str], job_description: str, strictness: str = "normal", balance: float = 0.5
) -> list[float]:
    return [row["display_score"] for row in score_cvs_to_job(
        cv_texts, job_description, strictness=strictness, balance=balance
    )]


def compare_cv_to_job(
    cv_text: str, job_description: str, strictness: str = "normal", balance: float = 0.5
) -> float:
    scores = compare_cvs_to_job([cv_text], job_description, strictness, balance)
    return scores[0] if scores else 0.0


def compare_cvs_to_criteria(
    cv_texts: list[str],
    weighted_criteria: list[tuple[str, float]],
    strictness: str = "normal",
    balance: float = 0.5,
) -> list[float]:
    compatibility = [
        ({"id": f"criterion-{index}", "label": text, "priority": "important"}, [text], weight)
        for index, (text, weight) in enumerate(weighted_criteria, start=1)
    ]
    return [row["display_score"] for row in score_cvs_to_criteria(
        cv_texts, compatibility, strictness=strictness, balance=balance
    )]


def compare_cv_to_criteria(
    cv_text: str,
    weighted_criteria: list[tuple[str, float]],
    strictness: str = "normal",
    balance: float = 0.5,
) -> float:
    scores = compare_cvs_to_criteria([cv_text], weighted_criteria, strictness, balance)
    return scores[0] if scores else 0.0
