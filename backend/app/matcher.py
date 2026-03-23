from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = None

def get_model():
    global model
    if model is None:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    return model

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal") -> float:
    m = get_model()
    cv_embedding = m.encode(cv_text)
    job_embedding = m.encode(job_description)
    base_score = float(cosine_similarity([cv_embedding], [job_embedding])[0][0])

    KEYWORDS_PENALTY = [
        "ventas", "sales", "comercial", "erp", "sap", "plc", "soldadura",
        "react", "python", "javascript", "sql", "salesforce", "hubspot"
    ]

    cv_lower = cv_text.lower()
    job_lower = job_description.lower()

    if strictness == "estricto":
        critical_missing = [k for k in KEYWORDS_PENALTY if k in job_lower and k not in cv_lower]
        penalty = len(critical_missing) * 0.06
    elif strictness == "normal":
        critical_missing = [k for k in KEYWORDS_PENALTY if k in job_lower and k not in cv_lower]
        penalty = len(critical_missing) * 0.03
    else:
        penalty = 0.0

    return round(max(0.0, min(1.0, base_score - penalty)), 2)