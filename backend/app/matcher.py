import os
import json
import requests
import numpy as np

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def get_embedding(text: str) -> list:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "nomic-embed-text-v1_5",
        "input": text
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/embeddings",
        headers=headers,
        json=body,
        timeout=30
    )
    return response.json()["data"][0]["embedding"]

def cosine_similarity_manual(a, b) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def compare_cv_to_job(cv_text: str, job_description: str) -> float:
    cv_embedding = get_embedding(cv_text)
    job_embedding = get_embedding(job_description)
    return cosine_similarity_manual(cv_embedding, job_embedding)