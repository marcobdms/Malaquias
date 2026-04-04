from sentence_transformers import SentenceTransformer, util
from rank_bm25 import BM25Okapi
import re

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

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal", balance: float = 0.5) -> float:
    if model is None:
        return 0.0

    # Sentence score
    cv_emb = model.encode([cv_text])
    job_emb = model.encode([job_description])
    sentence_score = float(util.cos_sim(cv_emb, job_emb)[0][0])

    # BM25 score
    cv_tokens = tokenize(cv_text)
    job_tokens = tokenize(job_description)
    bm25 = BM25Okapi([cv_tokens])
    raw_bm25 = bm25.get_scores(job_tokens)[0]
    bm25_score = float(raw_bm25 / (raw_bm25 + 1))

    # Hybrid
    hybrid = (balance * bm25_score) + ((1 - balance) * sentence_score)

    if strictness == "estricto":
        final = (hybrid - 0.5) / 0.5
    elif strictness == "normal":
        final = (hybrid - 0.3) / 0.7
    else:
        final = hybrid

    result = round(max(0.0, min(1.0, final)), 2)
    print(f"DEBUG sentence={sentence_score:.3f} bm25={bm25_score:.3f} hybrid={hybrid:.3f} final={result}")
    return result