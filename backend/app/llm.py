"""Optional LLM explanations.

The ranking engine never depends on this module: providers only turn already
calculated results into a human-readable explanation.  Every public entry point
is fail-open and returns an ``error`` object instead of raising.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import os
import threading
import time
from typing import Any, Callable, Mapping, Protocol

import requests

from .config import load_environment


load_environment()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ALLOWED_RECOMMENDATIONS = {"Entrevistar", "Considerar", "Descartar"}

EXPLANATION_SCHEMA = {
    "type": "object",
    "properties": {
        "nombre_candidato": {"type": "string"},
        "titulo_candidato": {"type": "string"},
        "fortalezas": {"type": "array", "items": {"type": "string"}},
        "carencias": {"type": "array", "items": {"type": "string"}},
        "valoracion": {"type": "string"},
        "recomendacion": {
            "type": "string",
            "enum": sorted(ALLOWED_RECOMMENDATIONS),
        },
        "email_candidato": {"type": "string", "nullable": True},
        "telefono_candidato": {"type": "string", "nullable": True},
    },
    "required": [
        "nombre_candidato",
        "titulo_candidato",
        "fortalezas",
        "carencias",
        "valoracion",
        "recomendacion",
        "email_candidato",
        "telefono_candidato",
    ],
}


class LLMError(RuntimeError):
    """A provider failed without exposing its response body or credentials."""


class LLMProvider(Protocol):
    name: str
    model: str

    def generate(self, prompt: str) -> Mapping[str, Any]: ...


def _positive_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


class _RateLimiter:
    def __init__(self, min_interval: float, clock: Callable[[], float] = time.monotonic):
        self.min_interval = min_interval
        self.clock = clock
        self._last_request = 0.0
        self._lock = threading.Lock()

    def wait(self, sleeper: Callable[[float], None]) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = self.clock()
            delay = self.min_interval - (now - self._last_request)
            if delay > 0:
                sleeper(delay)
            self._last_request = self.clock()


def _retry_after_seconds(value: str | None, now: datetime | None = None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            current = now or datetime.now(timezone.utc)
            return max(0.0, (retry_at - current).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


@dataclass
class _HTTPClient:
    session: Any = requests
    sleeper: Callable[[float], None] = time.sleep
    max_attempts: int = 3
    timeout: float = 30.0
    min_interval: float = 0.0

    def __post_init__(self) -> None:
        self._limiter = _RateLimiter(self.min_interval)

    def post(self, url: str, *, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        last_status: int | None = None
        for attempt in range(self.max_attempts):
            self._limiter.wait(self.sleeper)
            try:
                response = self.session.post(url, headers=headers, json=body, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt + 1 < self.max_attempts:
                    self.sleeper(min(2**attempt, 8))
                    continue
                raise LLMError("No se pudo contactar con el proveedor LLM") from exc

            last_status = response.status_code
            if 200 <= response.status_code < 300:
                try:
                    payload = response.json()
                except (ValueError, json.JSONDecodeError) as exc:
                    raise LLMError("El proveedor LLM devolvió una respuesta no válida") from exc
                if not isinstance(payload, dict):
                    raise LLMError("El proveedor LLM devolvió una respuesta no válida")
                return payload

            retryable = response.status_code == 429 or 500 <= response.status_code < 600
            if retryable and attempt + 1 < self.max_attempts:
                retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                self.sleeper(retry_after if retry_after is not None else min(2**attempt, 8))
                continue
            break

        status = f" ({last_status})" if last_status is not None else ""
        raise LLMError(f"El proveedor LLM no está disponible{status}")


def _extract_json(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str):
        raise LLMError("El proveedor LLM no devolvió JSON")
    raw = value.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError("El proveedor LLM no devolvió JSON válido") from exc
    if not isinstance(payload, Mapping):
        raise LLMError("El proveedor LLM no devolvió un objeto JSON")
    return payload


def _validate_string(payload: Mapping[str, Any], key: str, max_length: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LLMError(f"Respuesta LLM inválida: {key}")
    return value.strip()[:max_length]


def _validate_optional_string(payload: Mapping[str, Any], key: str, max_length: int) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise LLMError(f"Respuesta LLM inválida: {key}")
    value = value.strip()
    return value[:max_length] if value else None


def _validate_list(payload: Mapping[str, Any], key: str, max_items: int) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise LLMError(f"Respuesta LLM inválida: {key}")
    clean = [item.strip()[:300] for item in value if isinstance(item, str) and item.strip()]
    if not clean:
        raise LLMError(f"Respuesta LLM inválida: {key}")
    return clean[:max_items]


def validate_explanation(payload: Mapping[str, Any]) -> dict[str, Any]:
    recommendation = _validate_string(payload, "recomendacion", 20)
    if recommendation not in ALLOWED_RECOMMENDATIONS:
        raise LLMError("Respuesta LLM inválida: recomendacion")
    return {
        "nombre_candidato": _validate_string(payload, "nombre_candidato", 150),
        "titulo_candidato": _validate_string(payload, "titulo_candidato", 80),
        "fortalezas": _validate_list(payload, "fortalezas", 5),
        "carencias": _validate_list(payload, "carencias", 5),
        "valoracion": _validate_string(payload, "valoracion", 1200),
        "recomendacion": recommendation,
        "email_candidato": _validate_optional_string(payload, "email_candidato", 254),
        "telefono_candidato": _validate_optional_string(payload, "telefono_candidato", 50),
    }


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, client: _HTTPClient):
        self.api_key = api_key
        self.model = model
        self.client = client

    def generate(self, prompt: str) -> Mapping[str, Any]:
        payload = self.client.post(
            GEMINI_URL.format(model=self.model),
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            body={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 700,
                    "responseMimeType": "application/json",
                    "responseSchema": EXPLANATION_SCHEMA,
                },
            },
        )
        try:
            return _extract_json(payload["candidates"][0]["content"]["parts"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Gemini devolvió una respuesta incompleta") from exc


class _MemoryCache:
    """Small, process-local cache. Keys are hashes; persistence is intentionally forbidden."""

    def __init__(self, max_entries: int = 128):
        self.max_entries = max_entries
        self._values: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str, ttl: float) -> dict[str, Any] | None:
        if ttl <= 0:
            return None
        with self._lock:
            item = self._values.get(key)
            if item is None:
                return None
            created, value = item
            if time.monotonic() - created > ttl:
                self._values.pop(key, None)
                return None
            self._values.move_to_end(key)
            return dict(value)

    def put(self, key: str, value: dict[str, Any], ttl: float) -> None:
        if ttl <= 0:
            return
        with self._lock:
            self._values[key] = (time.monotonic(), dict(value))
            self._values.move_to_end(key)
            while len(self._values) > self.max_entries:
                self._values.popitem(last=False)


_CACHE = _MemoryCache()
_CLIENTS: dict[tuple[int, float, float], _HTTPClient] = {}
_CLIENTS_LOCK = threading.Lock()


def _build_client() -> _HTTPClient:
    settings = (
        _positive_int("LLM_MAX_ATTEMPTS", 3),
        _positive_float("LLM_TIMEOUT_SECONDS", 30.0),
        _positive_float("LLM_MIN_INTERVAL_SECONDS", 0.0),
    )
    with _CLIENTS_LOCK:
        if settings not in _CLIENTS:
            _CLIENTS[settings] = _HTTPClient(
                max_attempts=settings[0],
                timeout=settings[1],
                min_interval=settings[2],
            )
        return _CLIENTS[settings]


def get_provider() -> LLMProvider | None:
    requested = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    if requested in {"", "none", "disabled", "off"}:
        return None
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if requested == "auto":
        requested = "gemini" if gemini_key else "none"
    client = _build_client()
    if requested == "gemini":
        return GeminiProvider(gemini_key, os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"), client) if gemini_key else None
    raise LLMError(f"Proveedor LLM desconocido: {requested}")


def _build_prompt(cv_text: str, job_description: str, categoria: str, stack: str, strictness: str) -> str:
    context = []
    if categoria:
        context.append(f"Categoría del puesto: {categoria}")
    if stack:
        context.append(f"Requisitos técnicos indicados: {stack}")
    tone = "Sé exigente y basa cada afirmación en evidencia del CV." if strictness == "estricto" else "Sé equilibrado y distingue evidencia de aspectos por verificar."
    return f"""Analiza el CV frente a la oferta para explicar coincidencias y aspectos por verificar.
No calcules, ajustes ni menciones ningún score. El ranking se calcula en otro sistema independiente.
No inventes experiencia, identidad ni datos de contacto. Si un dato de contacto no aparece, usa null.
{tone}
{' '.join(context)}

OFERTA:
{job_description}

CV:
{cv_text}

Devuelve únicamente un objeto JSON según este esquema:
{json.dumps(EXPLANATION_SCHEMA, ensure_ascii=False)}
"""


def analyze_with_llm(
    cv_text: str,
    job_description: str,
    categoria: str = "",
    stack: str = "",
    strictness: str = "normal",
    match_score: float = 0.0,
) -> dict[str, Any]:
    """Generate optional narrative evidence; never alter or gate ``match_score``.

    ``match_score`` remains in the signature for backwards compatibility but is
    intentionally not sent to providers.
    """
    del match_score
    try:
        provider = get_provider()
        if provider is None:
            return {"error": "Explicación LLM no disponible", "provider": None}
        prompt = _build_prompt(cv_text, job_description, categoria, stack, strictness)
        cache_key = hashlib.sha256(
            f"v2\0{provider.name}\0{provider.model}\0{prompt}".encode("utf-8")
        ).hexdigest()
        cache_ttl = _positive_float("LLM_CACHE_TTL_SECONDS", 0.0)
        cached = _CACHE.get(cache_key, cache_ttl)
        if cached is not None:
            return cached
        result = validate_explanation(provider.generate(prompt))
        _CACHE.put(cache_key, result, cache_ttl)
        return result
    except LLMError as exc:
        return {"error": str(exc), "provider": getattr(locals().get("provider"), "name", None)}
    except Exception:
        return {"error": "Error inesperado al generar la explicación", "provider": None}
