import requests
import os
import numpy as np

HF_TOKEN = os.getenv("HF_TOKEN")
API_URL = "https://router.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
def get_embedding(text: str) -> list:
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": text}
    )
    result = response.json()
    
    if isinstance(result, dict):
        raise ValueError(f"Error de Hugging Face: {result}")
    
    return result

def cosine_similarity_manual(a, b) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def compare_cv_to_job(cv_text: str, job_description: str) -> float:
    cv_embedding = get_embedding(cv_text)
    job_embedding = get_embedding(job_description)
    return cosine_similarity_manual(cv_embedding, job_embedding)