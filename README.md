# Malaquías — CV Screening con IA

> Motor de cribado de candidatos impulsado por inteligencia artificial. Analiza CVs en PDF frente a ofertas de trabajo y genera rankings, análisis narrativos y recomendaciones de contratación.

![Stack](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square)
![Stack](https://img.shields.io/badge/Frontend-React_+_Vite-61DAFB?style=flat-square)
![Stack](https://img.shields.io/badge/LLM-Groq_LLaMA_3-orange?style=flat-square)
![Stack](https://img.shields.io/badge/DB-Supabase-3ECF8E?style=flat-square)
![License](https://img.shields.io/badge/License-AGPL--3.0-blue?style=flat-square)

-----

## ¿Qué hace Malaquías?

Malaquías es una aplicación web para reclutadores que permite:

- Subir hasta 20 CVs en PDF y compararlos contra una oferta de trabajo
- Obtener un **score de compatibilidad** calculado con un motor híbrido (semántico + keyword)
- Recibir un **análisis narrativo** generado por LLM con fortalezas, carencias y valoración
- Ver el **nombre real del candidato** y su cargo extraídos automáticamente del CV
- Filtrar por categoría de puesto (IT, Desarrollo, Ventas, Logística, etc.)
- Guardar análisis históricos por oferta
- Contactar candidatos directamente si el CV incluye datos de contacto

-----

## Stack tecnológico

|Capa            |Tecnología                             |
|----------------|---------------------------------------|
|Backend API     |FastAPI (Python 3.12)                  |
|Motor de scoring|Sentence-transformers + Keyword híbrido|
|LLM             |Groq API (llama-3.1-8b-instant)        |
|Base de datos   |Supabase (PostgreSQL)                  |
|Autenticación   |JWT + confirmación por email (Resend)  |
|Frontend        |React + Vite + Tailwind CSS            |
|Hosting backend |Coolify en Hetzner VPS                 |
|Hosting frontend|Vercel                                 |

-----

## Estructura del proyecto

```
Malaquias/
├── backend/
│   ├── app/
│   │   ├── main.py              # Endpoints FastAPI
│   │   ├── matcher.py           # Motor de scoring híbrido
│   │   ├── keyword_matcher.py   # Keyword score
│   │   ├── llm.py               # Integración Groq API
│   │   ├── cv_parser.py         # Extracción texto PDF
│   │   ├── auth.py              # JWT auth
│   │   ├── models.py            # Modelos SQLAlchemy
│   │   ├── database.py          # Conexión Supabase
│   │   ├── email_service.py     # Emails con Resend
│   │   └── utils.py             # Utilidades
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   └── Confirm.jsx
│   │   └── components/
│   │       ├── Navbar.jsx
│   │       ├── Sidebar.jsx
│   │       ├── JobForm.jsx
│   │       ├── DropZone.jsx
│   │       ├── Results.jsx
│   │       ├── Progress.jsx
│   │       └── Dashboard.jsx
│   └── package.json
└── benchmark/                   # Laboratorio de pruebas del motor
```

-----

## Instalación local

### Requisitos previos

- Python 3.10+
- Node.js 18+
- API key de Groq para activar el análisis LLM

El desarrollo local usa SQLite por defecto y no necesita conectarse a Supabase ni a una base de producción.

### Preparación

```bash
python -m venv .venv
pip install -r backend/requirements.txt
npm install
npm --prefix frontend install
```

Copia `.env.local.example` como `.env.local` y utiliza una clave exclusivamente local. Para Vite, copia también `frontend/.env.local.example` como `frontend/.env.local`.

### Frontend y backend juntos

```bash
npm run dev
```

La terminal identifica los procesos como `[FRONT]` y `[BACK]`. La app queda en `http://localhost:5173` y la API en `http://localhost:8000/docs`.

Los despliegues deben inyectar las variables documentadas en `.env.example`. No reutilices `.env.local` en producción. Los futuros cambios estructurales de base de datos se publicarán como migraciones.

-----

## Variables de entorno

|Variable        |Descripción                 |Dónde obtenerla               |
|----------------|----------------------------|------------------------------|
|`GROQ_API_KEY`  |API key de Groq             |console.groq.com              |
|`DATABASE_URL`  |Connection string PostgreSQL|Supabase → Settings → Database|
|`SECRET_KEY`    |Clave para firmar JWT       |Generar localmente            |
|`RESEND_API_KEY`|API key de Resend           |resend.com                    |
|`FRONTEND_URL`  |URL del frontend            |Tu dominio de Vercel          |

El frontend utiliza además `VITE_API_URL`, documentada en `frontend/.env.example`.

-----

## Benchmark v2

El laboratorio público vive en [`benchmark/`](benchmark/README.md) y empieza desde cero. Separa lectura de documentos, interpretación de criterios y ranking, y mantiene fuera de Git los datasets descargados, los CV privados y los resultados locales.

```bash
python benchmark/scripts/fetch_sources.py --list
python benchmark/scripts/fetch_sources.py ecyl_open_jobs
```

Los contratos JSON de vacante, candidato y evaluación están versionados en `benchmark/schemas/`. Consulta también [`DESIGN.md`](DESIGN.md) para el sistema visual y el vocabulario de producto.

-----

## Motor de scoring

Malaquías utiliza un motor híbrido con dos componentes:

**Semántico** — Sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) calcula similitud vectorial entre el CV y la oferta. Entiende sinónimos y contexto.

**Keyword** — Intersección de términos relevantes entre CV y oferta, con escala adaptativa. Detecta keywords técnicas exactas.

**Score final:**

```
score = (balance × keyword_score) + ((1 - balance) × sentence_score)
```

El parámetro `balance` (0.0–1.0) controla el peso de cada componente. Por defecto 0.5 (híbrido equilibrado).

-----

## Ramas

|Rama                           |Descripción                                       |
|-------------------------------|--------------------------------------------------|
|`main`                         |Versión estable en producción                     |
|`v0.1.2`                       |Versión inicial sin diseño Crystal Editorial      |
|`feature/sentence-transformers`|Rama experimental con sentence-transformers pesado|

-----

## Roadmap

- [ ] Panel de opciones avanzadas (filtros obligatorios, slider semántico/técnico)
- [ ] Router adaptativo del motor según número de CVs
- [ ] N-gramas para captura de términos compuestos
- [ ] Cross-encoder para modo análisis exhaustivo
- [ ] Laboratorio de benchmark con métricas NDCG
- [ ] Fine-tuning del modelo con datos propios
- [ ] Rate limiting y refresh tokens JWT
- [ ] OCR para capturas de pantalla de ATS

-----

## Licencia

Malaquías está dedicado al dominio público mediante CC0 1.0. Puede usarse, copiarse, modificarse y redistribuirse libremente. Consulta [`LICENSE`](LICENSE).
