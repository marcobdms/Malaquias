from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = None

def get_model():
    global model
    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    return model

def compare_cv_to_job(cv_text: str, job_description: str) -> float:
    m = get_model()
    cv_embedding = m.encode(cv_text)
    job_embedding = m.encode(job_description)
    score = cosine_similarity([cv_embedding], [job_embedding])[0][0]
    return float(score)