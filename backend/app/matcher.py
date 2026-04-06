from sentence_transformers import SentenceTransformer, util
import re
import math

print("Cargando modelo SentenceTransformer...")
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"Error cargando modelo: {e}")
    model = None

STOPWORDS = {"de","la","el","en","y","a","que","con","por","para","los","las","un","una","es","se","del","al","lo","su","sus","si","no","yo","mi"}

def tokenize(text: str) -> list:
    tokens = re.findall(r'\b\w+\b', text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]

def get_ngrams(tokens: list, n: int = 2) -> list:
    """Genera n-gramas a partir de una lista de tokens."""
    return [' '.join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

def keyword_score(cv_text: str, job_description: str) -> float:
    cv_tokens = set(tokenize(cv_text))
    job_tokens = tokenize(job_description)
    
    if not job_tokens:
        return 0.0
    
    job_unique = set(job_tokens)
    matches = len(cv_tokens & job_unique)
    score = matches / len(job_unique)
    return min(1.0, score * 2.5)

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal", balance: float = 0.5) -> float:
    if model is None:
        return 0.0

    cv_emb = model.encode([cv_text])
    job_emb = model.encode([job_description])
    sentence_score = float(util.cos_sim(cv_emb, job_emb)[0][0])

    kw_score = keyword_score(cv_text, job_description)

    hybrid = (balance * kw_score) + ((1 - balance) * sentence_score)

    if strictness == "estricto":
        final = (hybrid - 0.4) / 0.6
    elif strictness == "normal":
        final = (hybrid - 0.2) / 0.8
    else:
        final = hybrid

    result = round(max(0.0, min(1.0, final)), 2)
    print(f"DEBUG sentence={sentence_score:.3f} kw={kw_score:.3f} hybrid={hybrid:.3f} final={result}")
    return result