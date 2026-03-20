from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer("all-MiniLM-L6-v2")

def compare_cv_to_job(cv_text: str, job_description: str) -> float:
    cv_embedding = model.encode(cv_text)
    job_embedding = model.encode(job_description)
    score = cosine_similarity([cv_embedding], [job_embedding])[0][0]
    return float(score)