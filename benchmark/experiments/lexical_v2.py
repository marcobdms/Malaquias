"""Matcher léxico interpretable para experimentar con criterios discriminantes.

Este módulo no sustituye al matcher de producción. Su contrato pequeño permite
compararlo en benchmarks antes de decidir si alguna parte debe promocionarse.
Las equivalencias se evalúan como alternativas OR y nunca como requisitos
acumulativos.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any


# Palabras frecuentes que, aisladas, describen demasiados puestos para probar
# una competencia. Se conservan con un peso residual para hacer el diagnóstico
# visible, pero no pueden confirmar por sí solas un criterio.
GENERIC_TERMS = {
    "analisis", "analytical", "analysis", "analyze", "analizar",
    "datos", "data", "documentacion", "documentation", "document",
    "experiencia", "experience", "gestion", "management", "manager",
    "informe", "informes", "report", "reporting", "resultados", "results",
    "proyecto", "proyectos", "project", "projects", "requisitos", "requirements",
    "resolucion", "solving", "soporte", "support", "tecnico", "tecnica",
    "technical", "trabajo", "work", "equipo", "team", "calidad", "quality",
    "edificio", "edificios", "facility", "facilities", "instalacion", "instalaciones",
    "sede", "sedes", "servicio", "servicios",
}

STOPWORDS = {
    "a", "al", "and", "con", "de", "del", "el", "en", "for", "la", "las",
    "los", "of", "or", "para", "por", "the", "to", "un", "una", "y",
}

NEGATION_MARKERS = {
    "carece", "carezco", "ni", "ningun", "ninguna", "no", "nunca", "sin",
    "without", "lack", "lacks", "lacking", "neither", "nor",
}


# Expansiones acotadas a un concepto. Solo se activan si el criterio ya contiene
# una de las claves del grupo; nunca se añaden a todos los criterios.
DOMAIN_ALIAS_GROUPS = (
    {
        "scope": "failure_root_cause",
        "activation": {
            "analisis de fallas", "analisis de falla", "failure analysis",
            "causa raiz", "root cause analysis", "rca",
        },
        "aliases": {
            "analisis de fallas", "analisis de falla", "failure analysis",
            "analisis de causa raiz", "determinacion de causa raiz",
            "root cause analysis", "rca", "fmea", "amfe",
            "analisis de modo de falla y efectos",
            "analisis modal de fallos y efectos",
        },
        "anchors": {
            "falla", "fallas", "fallo", "fallos", "failure", "root", "raiz",
            "rca", "fmea", "amfe",
        },
    },
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text).casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", without_accents))


def _tokens(text: str) -> list[str]:
    return _normalize(text).split()


def _deduplicate(values: Sequence[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in values:
        normalized = _normalize(raw)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append((str(raw).strip(), normalized))
    return result


def _domain_expansion(
    primary_label: str,
    requested_scopes: set[str],
) -> tuple[list[str], set[str]]:
    """Expande solo el concepto primario o un scope declarado explícitamente.

    Las equivalencias pueden contener contexto compartido con otros criterios
    (por ejemplo, «validación de causa raíz» dentro de planes de prueba). Usarlas
    para activar el grupo propagaría FMEA a competencias diferentes.
    """

    expanded: set[str] = set()
    anchors: set[str] = set()
    for group in DOMAIN_ALIAS_GROUPS:
        activation = group["activation"]
        label_activates = any(
            key == primary_label or key in primary_label for key in activation
        )
        scope_activates = group["scope"] in requested_scopes
        if label_activates or scope_activates:
            expanded.update(group["aliases"])
            anchors.update(group["anchors"])
    return sorted(expanded), anchors


def _is_negated(candidate_tokens: Sequence[str], start: int) -> bool:
    # Una ventana pequeña cubre "sin experiencia demostrable en X" sin arrastrar
    # una negación perteneciente a una frase muy anterior.
    prefix = candidate_tokens[max(0, start - 6):start]
    return any(token in NEGATION_MARKERS for token in prefix)


def _find_exact_hits(candidate_tokens: Sequence[str], phrase_tokens: Sequence[str]) -> list[int]:
    size = len(phrase_tokens)
    if not size or size > len(candidate_tokens):
        return []
    return [
        index
        for index in range(len(candidate_tokens) - size + 1)
        if list(candidate_tokens[index:index + size]) == list(phrase_tokens)
    ]


def _token_weight(token: str) -> float:
    if token in STOPWORDS:
        return 0.0
    if token in GENERIC_TERMS:
        return 0.12
    return 1.0


def _score_alternative(
    candidate_tokens: Sequence[str],
    raw: str,
    normalized: str,
    anchor_tokens: set[str],
    source: str,
    positive_candidate_set: set[str] | None = None,
) -> dict[str, Any]:
    phrase_tokens = normalized.split()
    exact_hits = _find_exact_hits(candidate_tokens, phrase_tokens)
    positive_hits = [index for index in exact_hits if not _is_negated(candidate_tokens, index)]
    negated_hits = [index for index in exact_hits if _is_negated(candidate_tokens, index)]

    meaningful = [token for token in phrase_tokens if token not in STOPWORDS]
    specific = [token for token in meaningful if token not in GENERIC_TERMS]
    if positive_candidate_set is None:
        positive_candidate_set = {
            token for index, token in enumerate(candidate_tokens)
            if not _is_negated(candidate_tokens, index)
        }
    matched = sorted({token for token in meaningful if token in positive_candidate_set})
    matched_specific = sorted(set(specific) & positive_candidate_set)
    matched_anchors = sorted(anchor_tokens & set(phrase_tokens) & positive_candidate_set)

    if positive_hits:
        # Una frase exacta que solo contiene vocabulario genérico sigue sin probar
        # una competencia. Una sigla o término específico exacto sí es una señal
        # léxica completa.
        score = 1.0 if specific or matched_anchors else 0.25
        reason = "exact_phrase" if score == 1.0 else "generic_exact_phrase"
    elif negated_hits and not matched_specific:
        score = 0.0
        reason = "negated"
    else:
        denominator = sum(_token_weight(token) for token in meaningful)
        numerator = sum(_token_weight(token) for token in set(matched))
        coverage = numerator / denominator if denominator else 0.0
        has_anchor = bool(matched_anchors)

        if not matched_specific:
            # "análisis" o "documentación" aislados quedan deliberadamente lejos
            # de cualquier umbral de confirmación.
            score = min(0.12, coverage)
            reason = "generic_overlap" if matched else "no_match"
        elif has_anchor:
            # Las anclas de dominio inferidas ayudan a explicar el solapamiento,
            # pero una palabra parcial no debe confirmar un obligatorio.
            score = min(0.55, max(0.35, coverage))
            reason = "anchor_overlap"
        else:
            # Solapamiento parcial específico, pero sin una frase o ancla completa.
            score = min(0.55, coverage)
            reason = "specific_partial_overlap"

    return {
        "alternative": raw,
        "normalized_alternative": normalized,
        "source": source,
        "score": round(float(score), 6),
        "reason": reason,
        "exact": bool(positive_hits),
        "matched_terms": matched,
        "matched_specific_terms": matched_specific,
        "matched_anchors": matched_anchors,
        "negated_exact_hits": len(negated_hits),
    }


def _score_explicit_anchor(
    candidate_tokens: Sequence[str], raw: str, normalized: str
) -> dict[str, Any]:
    """Evalúa el ancla como frase indivisible, nunca como bolsa de tokens."""

    phrase_tokens = normalized.split()
    exact_hits = _find_exact_hits(candidate_tokens, phrase_tokens)
    positive_hits = [index for index in exact_hits if not _is_negated(candidate_tokens, index)]
    negated_hits = [index for index in exact_hits if _is_negated(candidate_tokens, index)]
    meaningful = [token for token in phrase_tokens if token not in STOPWORDS]
    specific = [token for token in meaningful if token not in GENERIC_TERMS]
    if positive_hits and specific:
        score = 0.65
        reason = "exact_anchor_phrase"
    elif positive_hits:
        score = 0.12
        reason = "generic_anchor_phrase"
    elif negated_hits:
        score = 0.0
        reason = "negated_anchor"
    else:
        score = 0.0
        reason = "no_match"
    return {
        "alternative": raw,
        "normalized_alternative": normalized,
        "source": "explicit_anchor",
        "score": score,
        "reason": reason,
        "exact": bool(positive_hits),
        "matched_terms": meaningful if positive_hits else [],
        "matched_specific_terms": specific if positive_hits else [],
        "matched_anchors": [normalized] if positive_hits else [],
        "negated_exact_hits": len(negated_hits),
    }


def score_lexical_criterion(
    criterion: Mapping[str, Any],
    candidate_text: str,
) -> dict[str, Any]:
    """Puntúa evidencia léxica de un CV para un criterio.

    Entrada mínima: ``{"label": str, "equivalences": list[str]}``. Opcionalmente
    acepta ``anchor_terms``. El score pertenece a [0, 1] y el diagnóstico indica
    qué alternativa OR ganó y por qué. No usa embeddings ni servicios externos.
    """

    compiled = compile_lexical_criterion(criterion)
    return score_compiled_criteria([compiled], candidate_text)[0]


def compile_lexical_criterion(criterion: Mapping[str, Any]) -> dict[str, Any]:
    """Precompila un criterio; seguro para reutilizarlo con muchos CV."""

    label = str(criterion.get("label") or "").strip()
    if not label:
        raise ValueError("criterion.label no puede estar vacío")

    raw_equivalences = criterion.get("equivalences") or []
    if isinstance(raw_equivalences, (str, bytes)) or not isinstance(raw_equivalences, Sequence):
        raise ValueError("criterion.equivalences debe ser una lista")

    explicit = _deduplicate([label, *(str(value) for value in raw_equivalences if str(value).strip())])
    raw_scopes = criterion.get("domain_alias_scope") or []
    if isinstance(raw_scopes, (str, bytes)):
        raw_scopes = [raw_scopes]
    if not isinstance(raw_scopes, Sequence):
        raise ValueError("criterion.domain_alias_scope debe ser string o lista")
    requested_scopes = {
        _normalize(str(scope)).replace(" ", "_")
        for scope in raw_scopes
        if str(scope).strip()
    }
    expanded_aliases, domain_anchors = _domain_expansion(
        _normalize(label), requested_scopes
    )
    expanded = _deduplicate(expanded_aliases)

    explicit_normalized = {normalized for _, normalized in explicit}
    all_alternatives = list(explicit)
    all_alternatives.extend(
        (raw, normalized) for raw, normalized in expanded if normalized not in explicit_normalized
    )

    raw_anchors = criterion.get("anchor_terms") or []
    if isinstance(raw_anchors, (str, bytes)):
        raw_anchors = [raw_anchors]
    if not isinstance(raw_anchors, Sequence):
        raise ValueError("criterion.anchor_terms debe ser una lista")
    explicit_anchors = _deduplicate(
        [str(anchor) for anchor in raw_anchors if str(anchor).strip()]
    )
    anchor_tokens = set(domain_anchors)

    return {
        "alternatives": [
            {
                "raw": raw,
                "normalized": normalized,
                "source": "criterion" if normalized in explicit_normalized else "domain_alias",
            }
            for raw, normalized in all_alternatives
        ],
        "explicit_anchors": explicit_anchors,
        "domain_anchor_tokens": anchor_tokens,
        "algorithm": "lexical-v2.2-experimental",
    }


def _score_compiled_criterion(
    compiled: Mapping[str, Any], candidate_tokens: Sequence[str]
) -> dict[str, Any]:
    positive_candidate_set = {
        token for index, token in enumerate(candidate_tokens)
        if not _is_negated(candidate_tokens, index)
    }
    evaluations = []
    for alternative in compiled["alternatives"]:
        evaluations.append(
            _score_alternative(
                candidate_tokens,
                alternative["raw"],
                alternative["normalized"],
                compiled["domain_anchor_tokens"],
                alternative["source"],
                positive_candidate_set,
            )
        )
    for raw, normalized in compiled["explicit_anchors"]:
        evaluations.append(_score_explicit_anchor(candidate_tokens, raw, normalized))

    winner = max(
        evaluations,
        key=lambda row: (
            row["score"], row["exact"], len(row["matched_anchors"]),
            len(row["matched_specific_terms"]),
        ),
    )
    negated = [
        {
            "alternative": row["alternative"],
            "source": row["source"],
            "hits": row["negated_exact_hits"],
        }
        for row in evaluations
        if row["negated_exact_hits"]
    ]

    return {
        "score": winner["score"],
        "matched": winner["score"] > 0.0,
        "matched_alternative": winner["alternative"] if winner["score"] > 0.0 else None,
        "match_source": winner["source"] if winner["score"] > 0.0 else None,
        "reason": winner["reason"],
        "matched_terms": winner["matched_terms"],
        "matched_specific_terms": winner["matched_specific_terms"],
        "matched_anchors": winner["matched_anchors"],
        "exact": winner["exact"],
        "negated_evidence": negated,
        "alternatives_evaluated": len(evaluations),
        "alternatives": evaluations,
        "algorithm": compiled["algorithm"],
    }


def score_compiled_criteria(
    compiled_criteria: Sequence[Mapping[str, Any]], candidate_text: str
) -> list[dict[str, Any]]:
    """Puntúa varios criterios precompilados tokenizando el CV una sola vez."""

    candidate_tokens = _tokens(candidate_text)
    return [
        _score_compiled_criterion(compiled, candidate_tokens)
        for compiled in compiled_criteria
    ]
