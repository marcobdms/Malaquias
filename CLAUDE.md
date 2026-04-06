# Malaquías — Contexto Global del Proyecto

## ¿Qué es Malaquías?
Aplicación web de screening de CVs con IA para reclutadores.
Analiza CVs en PDF contra ofertas de trabajo y genera rankings + análisis narrativos.

## Repositorio
https://github.com/marcobdms/Malaquias
Branch principal: main

## Stack completo
- Backend: FastAPI Python 3.12
- Motor scoring: sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) + keyword híbrido
- LLM: Groq API (llama-3.1-8b-instant)
- Base de datos: Supabase PostgreSQL
- Auth: JWT + confirmación email con Resend
- Frontend: React + Vite + Tailwind CSS
- Design system: Crystal Editorial (dark monochromático, sin teal/cyan)
- Hosting backend: Coolify en Hetzner VPS 8GB RAM, puerto 10000
- Hosting frontend: Vercel (malaquias-topaz.vercel.app)

## Estructura de archivos clave
```
backend/app/
├── main.py              # Endpoints FastAPI, SSE streaming /analyze
├── matcher.py           # Motor scoring híbrido (sentence + keyword)
├── keyword_matcher.py   # Keyword score puro
├── llm.py               # Groq API, extrae nombre/titulo/fortalezas/carencias
├── cv_parser.py         # Extracción texto de PDF con pypdf
├── auth.py              # JWT, hash passwords, get_current_user
├── models.py            # SQLAlchemy: User, Oferta, Candidato
├── database.py          # Conexión Supabase
├── email_service.py     # Resend emails confirmación
└── utils.py             # truncate_text, clean_text, validate_pdf_text

frontend/src/
├── App.jsx              # Estado global, routing simple con window.location
├── pages/Login.jsx      # Login + registro con JWT
├── pages/Confirm.jsx    # Confirmación email
├── components/Navbar.jsx
├── components/Sidebar.jsx
├── components/JobForm.jsx    # Categorías, stacks, severidad switcher
├── components/DropZone.jsx   # Drag & drop PDFs
├── components/Results.jsx    # Tarjetas candidatos expandibles
├── components/Progress.jsx   # Barra progreso SSE
└── components/Dashboard.jsx  # Análisis guardados
```

## Motor de scoring actual
```python
# matcher.py — score final
score = (balance * keyword_score) + ((1 - balance) * sentence_score)

# Normalización por severidad
if strictness == "estricto":   final = (score - 0.4) / 0.6
elif strictness == "normal":   final = (score - 0.2) / 0.8
else:                          final = score
```

## Schema JSON que devuelve el LLM (Groq)
```json
{
  "fortalezas": ["punto 1", "punto 2", "punto 3"],
  "carencias": ["punto 1", "punto 2"],
  "valoracion": "2-3 frases",
  "recomendacion": "Entrevistar|Considerar|Descartar",
  "email_candidato": "email o null",
  "telefono_candidato": "telefono o null",
  "nombre_candidato": "Nombre completo del CV",
  "titulo_candidato": "Cargo en máximo 30 chars"
}
```

## Parámetros del endpoint /analyze
- job_description: str
- categoria: Optional[str]
- stack: Optional[str]
- strictness: Optional[str] = "normal"
- balance: float = 0.5
- cvs: List[UploadFile]

## Reglas de código — SIEMPRE respetar
- No romper funcionalidad existente antes de modificar
- Crystal Editorial: monocromático oscuro, sin teal/cyan, sin sombras duras
- Colores: background #0a0a0a, surface #131313, zinc-500 labels, white activo
- Botones primarios: button-gradient (blanco a #d4d4d4), rounded-full
- El LLM siempre devuelve JSON estricto sin markdown
- SSE streaming obligatorio en /analyze
- Balance float 0.0-1.0 siempre disponible en matcher
- JWT token en header Authorization: Bearer {token}

## Variables de entorno necesarias
- GROQ_API_KEY
- DATABASE_URL (Supabase connection string)
- SECRET_KEY (JWT signing)
- RESEND_API_KEY
- FRONTEND_URL

## Pendiente implementar (NO tocar hasta que se indique)
- Slider semántico/técnico en UI (parámetro balance existe en backend)
- Panel opciones avanzadas (filtros obligatorios/deseables)
- Router adaptativo del motor
- N-gramas en keyword_score
- Cross-encoder modo exhaustivo
- Auto-detect categoría con LLM
