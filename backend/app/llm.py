import requests
import json
import os

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

def analyze_with_llm(cv_text: str, job_description: str, categoria: str = "", stack: str = "", strictness: str = "normal") -> dict:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"error": "GROQ_API_KEY no configurada"}

    filtros = ""
    if categoria:
        filtros += f"\nCategoría del puesto: {categoria}"
    if stack:
        filtros += f"\nRequisitos técnicos clave: {stack}"

    if strictness == "estricto":
        criterio = "Sé muy estricto. Solo recomienda 'Entrevistar' si el candidato cumple claramente los requisitos principales. Penaliza ausencia de experiencia directa."
    else:
        criterio = "Sé equilibrado. Valora el potencial y habilidades transferibles además de la experiencia directa."

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
        "Authorization": f"Bearer {api_key}",
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
        return {"error": f"Error Groq API: {e.response.status_code}", "detail": e.response.text}
    except json.JSONDecodeError:
        return {"error": "El LLM no devolvió JSON válido", "raw": raw}
    except Exception as e:
        return {"error": str(e)}