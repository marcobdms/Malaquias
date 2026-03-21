import os
import requests
import json

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def compare_cv_to_job(cv_text: str, job_description: str) -> float:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": "Eres un evaluador de CVs. Responde ÚNICAMENTE con un número decimal entre 0 y 1."
            },
            {
                "role": "user",
                "content": f"Evalúa qué tan bien encaja este CV con la oferta. Responde solo con un número entre 0.0 y 1.0.\n\nOFERTA:\n{job_description[:1000]}\n\nCV:\n{cv_text[:1000]}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 10
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30
        )
        raw = response.json()["choices"][0]["message"]["content"].strip()
        return float(raw)
    except Exception:
        return 0.0