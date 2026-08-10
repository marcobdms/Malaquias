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

def keyword_score(cv_text: str, job_description: str) -> float:
    cv_tokens = set(tokenize(cv_text))
    job_tokens = tokenize(job_description)
    
    if not job_tokens:
        return 0.0
    
    job_unique = set(job_tokens)
    matches = len(cv_tokens & job_unique)
    score = matches / len(job_unique)
    return min(1.0, score * 2.5)

def apply_strictness(score: float, strictness: str) -> float:
    if strictness == "estricto":
        adjusted = (score - 0.4) / 0.6
    elif strictness == "normal":
        adjusted = (score - 0.2) / 0.8
    else:
        adjusted = score
    return round(max(0.0, min(1.0, adjusted)), 2)

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal", balance: float = 0.5) -> float:
    if model is None:
        return 0.0

    embeddings = model.encode([cv_text, job_description])
    sentence_score = float(util.cos_sim(embeddings[0], embeddings[1]))

    kw_score = keyword_score(cv_text, job_description)

    hybrid = (balance * kw_score) + ((1 - balance) * sentence_score)

    result = apply_strictness(hybrid, strictness)
    print(f"DEBUG sentence={sentence_score:.3f} kw={kw_score:.3f} hybrid={hybrid:.3f} final={result}")
    return result

def compare_cv_to_criteria(
    cv_text: str,
    weighted_criteria: list[tuple[str, float]],
    strictness: str = "normal",
    balance: float = 0.5,
) -> float:
    """Evalúa criterios cortos en un solo lote y combina sus pesos explícitos."""

    if model is None or not weighted_criteria:
        return 0.0

    criterion_texts = [text for text, _ in weighted_criteria]
    embeddings = model.encode([cv_text, *criterion_texts])
    sentence_scores = util.cos_sim(embeddings[0], embeddings[1:])[0]

    weighted_total = 0.0
    total_weight = 0.0
    for index, (criterion_text, weight) in enumerate(weighted_criteria):
        sentence_score = float(sentence_scores[index])
        kw_score = keyword_score(cv_text, criterion_text)
        hybrid = (balance * kw_score) + ((1 - balance) * sentence_score)
        weighted_total += apply_strictness(hybrid, strictness) * weight
        total_weight += weight

    return round(weighted_total / total_weight, 2) if total_weight else 0.0
