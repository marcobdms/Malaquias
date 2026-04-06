# Workflow: Fase 3 — Motor Avanzado

## PRERREQUISITO
Este workflow solo se ejecuta DESPUÉS de que Fase 1 y Fase 2 estén completos y validados.
Lee CLAUDE.md y los resultados del benchmark antes de empezar.

## Contexto
Mejoras profundas al motor de scoring. Cada tarea es independiente y puede ejecutarse por separado.

## Tarea 1 — Chunking semántico en matcher.py
En lugar de encodear el CV completo como un vector, dividirlo en secciones.

```python
def extract_sections(cv_text: str) -> dict:
    """Divide el CV en secciones relevantes"""
    sections = {
        "experiencia": "",
        "habilidades": "",
        "formacion": "",
        "completo": cv_text
    }
    # Detectar secciones por keywords comunes en CVs españoles
    # experiencia: "experiencia", "professional", "trabajo", "empleo"
    # habilidades: "habilidades", "skills", "competencias", "conocimientos"
    # formacion: "formación", "educación", "estudios", "certificaciones"
    return sections

def sentence_score_chunked(cv_text: str, job_description: str) -> float:
    sections = extract_sections(cv_text)
    job_emb = model.encode([job_description])
    
    scores = []
    weights = {"experiencia": 0.5, "habilidades": 0.35, "formacion": 0.15}
    
    for section_name, weight in weights.items():
        if sections[section_name]:
            section_emb = model.encode([sections[section_name]])
            score = float(util.cos_sim(section_emb, job_emb)[0][0])
            scores.append(score * weight)
    
    return sum(scores) if scores else float(util.cos_sim(
        model.encode([cv_text]), job_emb)[0][0])
```

## Tarea 2 — Cross-encoder modo exhaustivo
Instalar: `pip install sentence-transformers` (ya instalado)
Modelo: `cross-encoder/ms-marco-MiniLM-L-6-v2`

```python
from sentence_transformers import CrossEncoder

cross_encoder = None

def get_cross_encoder():
    global cross_encoder
    if cross_encoder is None:
        cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return cross_encoder

def cross_encoder_score(cv_text: str, job_description: str) -> float:
    ce = get_cross_encoder()
    score = ce.predict([[job_description, cv_text[:512]]])[0]
    # normalizar score a 0-1
    import math
    return float(1 / (1 + math.exp(-score)))
```

Activar solo cuando `exhaustive=True` en el router y `num_cvs <= 5`.

## Tarea 3 — TF-IDF con scikit-learn
Alternativa matemática más robusta que el keyword score actual.

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

def tfidf_score(cv_text: str, job_description: str) -> float:
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        stop_words=list(STOPWORDS)
    )
    tfidf_matrix = vectorizer.fit_transform([cv_text, job_description])
    score = sk_cosine(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return float(score)
```

Scikit-learn ya está en requirements.txt.

## Tarea 4 — Panel opciones avanzadas en JobForm.jsx
Añadir sección colapsable "Opciones avanzadas" con:

A) Slider balance semántico/técnico (0-100, default 50)
B) Filtros obligatorios (eliminatorios):
   - Ubicación: input texto
   - Certificados: tag input (Enter para añadir, × para quitar)
   - Experiencia mínima: select (Sin filtro / +1 año / +2 años / +3 años / +5 años)
   - Idiomas: tag input
C) Switch "Análisis exhaustivo" (solo para ≤5 CVs, activa cross-encoder)
D) Filtros deseables: tag input

Pasar al FormData:
- balance: sliderValue / 100
- filtros_obligatorios: JSON.stringify({ubicacion, certificados, experiencia, idiomas})
- filtros_deseables: JSON.stringify(arrayDeseables)
- exhaustive: boolean

## Tarea 5 — Lógica de filtros en main.py
Pre-filtrado ANTES del LLM (costo cero en tokens):

```python
def check_mandatory_filters(cv_text: str, filtros: dict) -> tuple[bool, str]:
    """Returns (pasa_filtros, motivo_rechazo)"""
    cv_lower = cv_text.lower()
    
    if filtros.get("ubicacion"):
        if filtros["ubicacion"].lower() not in cv_lower:
            return False, f"No menciona ubicación: {filtros['ubicacion']}"
    
    for cert in filtros.get("certificados", []):
        if cert.lower() not in cv_lower:
            return False, f"No tiene certificado: {cert}"
    
    # experiencia: buscar patrones de años
    if filtros.get("experiencia"):
        min_years = int(filtros["experiencia"].replace("+", "").replace(" años", ""))
        import re
        years_found = re.findall(r'(\d+)\s*(?:año|year|yr)', cv_lower)
        total = sum(int(y) for y in years_found) if years_found else 0
        if total < min_years:
            return False, f"Experiencia insuficiente: {total} años (mínimo {min_years})"
    
    return True, ""
```

## Verificación después de cada tarea
- Benchmark Fase 2 debe mejorar o mantener métricas — nunca empeorar
- Backend arranca sin errores
- No se rompe el SSE streaming
