import requests
import json
import os
import time

# Configuración desde variables de entorno
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq") 
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
LLM_MODEL_LOCAL = os.getenv("LLM_MODEL", "llama3.1") # Cambiado a llama3.1 según tu setup
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

def analyze_with_llm(cv_text: str, job_description: str, categoria: str = "", stack: str = "", strictness: str = "normal", match_score: float = 0.0) -> dict:
    if LLM_PROVIDER == "groq" and not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY no configurada"}

    # Recorte preventivo para evitar 429 y optimizar contexto
    cv_text = cv_text[:1500] 
    job_description = job_description[:1000]
    score_pct = round(match_score * 100, 1)

    # Definición de la dureza del reclutador
    estricto_txt = "Sé implacable. Si no hay experiencia directa, descarta." if strictness == "estricto" else "Valora habilidades transferibles, pero mantente objetivo."

    system_prompt = f"""Eres un reclutador experto y analítico de la agencia 'Malaquías'. 
Tu misión es evaluar la afinidad real entre un CV y una oferta.
REGLA CRÍTICA: Eres un profesional objetivo, no un coach. Si el candidato NO es compatible, di 'Descartar'. 
No busques justificaciones forzadas para perfiles irrelevantes.
{estricto_txt}
Responde ÚNICAMENTE en formato JSON."""

    user_prompt = f"""OFERTA ({categoria}):
{job_description}
Requisitos técnicos clave: {stack}

CV DEL CANDIDATO:
{cv_text}

Score matemático previo: {score_pct}%

Genera un JSON con esta estructura:
{{
  "nombre_candidato": "Nombre completo",
  "titulo_candidato": "Cargo corto (max 30 carac.)",
  "llm_score": (int 0-100 basado en tu análisis),
  "fortalezas": ["Max 3 puntos clave"],
  "carencias": ["Puntos críticos faltantes (Siempre incluye al menos uno)"],
  "valoracion": "Máximo 2 frases directas.",
  "recomendacion": "Entrevistar|Considerar|Descartar",
  "email_candidato": "email o null",
  "telefono_candidato": "teléfono o null"
}}"""

    target_url = OLLAMA_URL if LLM_PROVIDER == "ollama" else GROQ_URL
    target_model = LLM_MODEL_LOCAL if LLM_PROVIDER == "ollama" else "llama-3.1-8b-instant"

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1, # Bajamos temperatura para mayor consistencia JSON
        "max_tokens": 600,
        "response_format": {"type": "json_object"} if LLM_PROVIDER == "groq" else None
    }

    headers = {"Content-Type": "application/json"}
    if LLM_PROVIDER == "groq":
        headers["Authorization"] = f"Bearer {GROQ_API_KEY}"

    # Ejecutamos sin reintentos automáticos
    for attempt in range(1):
        try:
            response = requests.post(target_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            
            # Limpieza básica de markdown si el modelo se olvida del system prompt
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content)

        except Exception as e:
            return {"error": f"Error en LLM: {str(e)}", "recomendacion": "Descartar", "valoracion": "Error técnico en el análisis."}