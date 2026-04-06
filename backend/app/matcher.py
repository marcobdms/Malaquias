from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = None

<<<<<<< Updated upstream
def get_model():
    global model
=======
STOPWORDS = {"de","la","el","en","y","a","que","con","por","para","los","las","un","una","es","se","del","al","lo","su","sus","si","no","yo","mi"}

def tokenize(text: str) -> list:
    tokens = re.findall(r'\b\w+\b', text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]

def get_ngrams(tokens: list, n: int = 2) -> list:
    """Genera n-gramas a partir de una lista de tokens."""
    return [' '.join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

def keyword_score(cv_text: str, job_description: str) -> float:
    cv_tokens_list = tokenize(cv_text)
    cv_unigrams = set(cv_tokens_list)
    cv_bigrams = set(get_ngrams(cv_tokens_list))
    cv_all = cv_unigrams | cv_bigrams

    job_tokens_list = tokenize(job_description)
    job_unigrams = set(job_tokens_list)
    job_bigrams = set(get_ngrams(job_tokens_list))
    job_all = job_unigrams | job_bigrams

    if not job_all:
        return 0.0

    matches = len(cv_all & job_all)
    score = matches / len(job_all)
    return min(1.0, score * 2.5)

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal", balance: float = 0.5) -> float:
>>>>>>> Stashed changes
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