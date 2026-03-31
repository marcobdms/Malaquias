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
    # convert_to_numpy=True para operaciones simples con arrays
    cv_emb = model.encode([cv_text])
    job_emb = model.encode([job_description])

    # Calculamos la similitud del coseno (Cosine Similarity)
    # util.cos_sim devuelve una matriz, tomamos el valor escalar
    cosine_sim = util.cos_sim(cv_emb, job_emb)
    score = float(cosine_sim[0][0])

    # El score de similitud semántica suele ser alto (0.4-0.9) incluso para perfiles no tan ideales
    # Ajustamos el rango para que sea más reactivo en el Dashboard
    if strictness == "estricto":
        final_score = (score - 0.5) / 0.5  # Escala 0.5-1.0 -> 0-1
    else:
        final_score = (score - 0.3) / 0.7  # Escala 0.3-1.0 -> 0-1

    return round(max(0.0, min(1.0, final_score)), 2)
