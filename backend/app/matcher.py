from sentence_transformers import SentenceTransformer, util
import numpy as np

# Cargamos el modelo globalmente para que persista en el proceso de FastAPI
# Usamos un modelo multilingüe balanceado (español/inglés)
print("Cargando modelo SentenceTransformer...")
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"Error cargando modelo: {e}")
    model = None

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal") -> float:
    """
    Calcula la similitud semántica entre el texto del CV y la descripción de la vacante.
    Ignora las penalizaciones por palabras clave concretas en favor del contexto global.
    """
    if model is None:
        return 0.0

    # Generamos los vectores (embeddings)
    cv_emb = model.encode([cv_text])
    job_emb = model.encode([job_description])

    # Calculamos la similitud del coseno
    cosine_sim = util.cos_sim(cv_emb, job_emb)
    score = float(cosine_sim[0][0])

    print(f"DEBUG - CV (trunc): {cv_text[:100]}...")
    print(f"DEBUG - JOB (trunc): {job_description[:100]}...")
    print(f"DEBUG - RAW SCORE: {score}")

    # Ajustamos el rango
    if strictness == "estricto":
        final_score = (score - 0.5) / 0.5
    else:
        # Menos estricto para evitar 0.0% en perfiles razonables
        final_score = (score - 0.25) / 0.75

    return round(max(0.0, min(1.0, final_score)), 2)
