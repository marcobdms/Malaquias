# Workflow: Fase 1 — Mejoras inmediatas al motor

## Contexto
Lee primero CLAUDE.md para entender el stack completo.
Lee estos archivos antes de hacer cualquier cambio:
- backend/app/matcher.py
- backend/app/keyword_matcher.py
- backend/app/main.py
- backend/app/llm.py
- frontend/src/components/JobForm.jsx
- frontend/src/App.jsx

## Tareas (implementar en este orden)

### Tarea 1 — N-gramas en keyword_matcher.py
Modifica la función `keyword_score` para capturar bigramas además de unigramas.
Ejemplo: "active directory" debe contar como una unidad, no como "active" y "directory" por separado.

```python
def get_ngrams(tokens, n=2):
    return [' '.join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]

# En keyword_score: combinar unigramas + bigramas del CV y del job
cv_unigrams = set(tokenize(cv_text))
cv_bigrams = set(get_ngrams(list(cv_unigrams)))
cv_all = cv_unigrams | cv_bigrams

job_tokens_list = tokenize(job_description)
job_unigrams = set(job_tokens_list)
job_bigrams = set(get_ngrams(job_tokens_list))
job_all = job_unigrams | job_bigrams
```

### Tarea 2 — Router adaptativo en main.py
Añade una función `route_engine` antes del endpoint /analyze:

```python
def route_engine(num_cvs: int, exhaustive: bool = False) -> dict:
    if exhaustive and num_cvs <= 5:
        return {"mode": "exhaustive", "llm_for_all": True}
    elif num_cvs <= 20:
        return {"mode": "hybrid", "llm_top_n": num_cvs}
    else:
        return {"mode": "keyword_only", "llm_top_n": 10}
```

En el loop de /analyze:
- Calcula scores matemáticos para TODOS los CVs primero
- Ordena por score
- Llama al LLM solo para los top N según el router
- Para los descartados devuelve solo el score sin análisis LLM

### Tarea 3 — Auto-detect categoría en llm.py
Añade función `detect_category` que se llama UNA vez antes del loop:

```python
def detect_category(job_description: str) -> dict:
    # Una llamada Groq que devuelve:
    # {"categoria": "it_sistemas", "keywords_criticas": ["vpn", "linux", "active directory"]}
    # Usar estas keywords_criticas en keyword_matcher para boost adicional
```

### Tarea 4 — Categorías en JobForm.jsx
Añade al array CATEGORIAS:
```js
{ value: 'it_sistemas', label: 'IT / Sistemas' },
{ value: 'data', label: 'Data / Analytics' },
{ value: 'devops', label: 'DevOps / Cloud' },
{ value: 'ciberseguridad', label: 'Ciberseguridad' },
{ value: 'finanzas', label: 'Finanzas' },
{ value: 'atencion_cliente', label: 'Atención al Cliente' },
```

Y en STACKS añade los correspondientes con keywords relevantes.

### Tarea 5 — Slider balance en JobForm.jsx
En el panel de opciones avanzadas (crear si no existe), añade:
- Slider range 0-100, default 50
- Label izquierda: "Semántico", derecha: "Técnico"
- Texto dinámico:
  - 0-30: "Prioriza perfil adaptable y potencial transferible"
  - 31-70: "Balance entre contexto y requisitos técnicos"
  - 71-100: "Prioriza keywords exactas y requisitos duros"
- Pasar valor al FormData como balance/100

## Verificación
Después de cada tarea, confirma que:
- uvicorn arranca sin errores
- /health devuelve {"status": "ok"}
- El endpoint /analyze acepta los mismos parámetros de antes
- No hay imports rotos
