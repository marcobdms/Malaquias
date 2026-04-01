import requests
import json
import os
import time

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def analyze_with_llm(cv_text: str, job_description: str, categoria: str = "", stack: str = "", strictness: str = "normal", match_score: float = 0.0) -> dict:
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY no configurada"}

    filtros = ""
    if categoria:
        filtros += f"\nCategoría del puesto: {categoria}"
    if stack:
        filtros += f"\nRequisitos técnicos clave: {stack}"

    score_pct = round(match_score * 100, 1)

    if strictness == "estricto":
        criterio = f"""Sé exigente pero justo. El score de similitud semántica es {score_pct}%.
Guía orientativa (no absoluta):
- Score < 10%: probablemente "Descartar", salvo que detectes potencial muy claro
- Score 10-25%: "Considerar" si hay señales positivas
- Score > 25%: evalúa libremente, "Entrevistar" si cumple requisitos principales
Penaliza la ausencia de experiencia directa en los requisitos clave."""
    else:
        criterio = f"""Sé equilibrado y valora el potencial. El score de similitud semántica es {score_pct}%.
Guía orientativa (no absoluta, usa tu criterio):
- Score < 10%: inclínate por "Descartar" o "Considerar"
- Score 10-20%: "Considerar" es lo más habitual
- Score > 20%: evalúa libremente, "Entrevistar" si hay buenas señales
Valora habilidades transferibles además de la experiencia directa."""

    prompt = f"""Analiza este CV frente a la oferta de trabajo.{filtros}

{criterio}

OFERTA:
{job_description}

CV:
{cv_text}

Responde ÚNICAMENTE con este JSON exacto, sin texto adicional:
{{
  "fortalezas": ["punto 1", "punto 2", "punto 3"],
  "carencias": ["punto 1", "punto 2"],
  "valoracion": "2-3 frases de valoración",
  "recomendacion": "Entrevistar",
  "email_candidato": "email@ejemplo.com o null",
  "telefono_candidato": "+34 600 000 000 o null"
}}

El campo recomendacion solo puede ser: "Entrevistar", "Considerar" o "Descartar"."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente de reclutamiento experto. Responde ÚNICAMENTE con JSON válido, sin texto adicional ni markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 600
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_URL, headers=headers, json=body, timeout=30)
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"].strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            return json.loads(raw)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                time.sleep(3 * (attempt + 1))
                continue
            return {"error": f"Error Groq API: {e.response.status_code}", "detail": e.response.text}
        except json.JSONDecodeError:
            return {"error": "El LLM no devolvió JSON válido", "raw": raw}
        except Exception as e:
            return {"error": str(e)}