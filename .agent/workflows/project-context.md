---
description: Contexto global del proyecto Malaquías - leer siempre antes de trabajar
---

# Malaquías — Contexto del Proyecto

## ¿Qué es?
Sistema de screening de CVs con IA. Un reclutador sube CVs en PDF, describe la oferta, y el sistema:
1. Calcula un **match score semántico** (SentenceTransformer local)
2. Genera un **análisis textual** con un LLM (Groq API / Llama 3.1 8B)
3. Muestra resultados ordenados con fortalezas, carencias, y recomendación

## Stack Técnico

### Backend (Python/FastAPI)
- **Ruta**: `backend/app/`
- **Framework**: FastAPI con Uvicorn
- **DB**: PostgreSQL en Supabase (SQLAlchemy ORM)
- **Auth**: JWT con python-jose, bcrypt
- **CV Parsing**: pypdf
- **Matching**: sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) — corre LOCAL
- **LLM**: Groq API (llama-3.1-8b-instant) — API externa
- **Emails**: Resend (limitado a 1 email verificado en free tier)
- **Deploy**: Coolify en VPS de 8GB RAM

### Frontend (React/Vite)
- **Ruta**: `frontend/src/`
- **Framework**: React 18 + Vite
- **CSS**: Tailwind CSS con design system custom (Crystal theme)
- **Variables de entorno**: `VITE_API_URL` para la URL del backend

### Archivos Clave
```
backend/app/
├── main.py          # FastAPI app, endpoints, SSE streaming
├── llm.py           # Integración Groq (análisis textual)
├── matcher.py       # SentenceTransformer (match score semántico)
├── cv_parser.py     # Extracción texto de PDF
├── models.py        # Modelos SQLAlchemy (User, Oferta, Candidato)
├── database.py      # Conexión PostgreSQL
├── auth.py          # JWT, hashing, get_current_user
├── email_service.py # Envío emails con Resend
└── utils.py         # clean_text, truncate_text, validate_pdf_text

frontend/src/
├── App.jsx          # Layout principal, lógica de análisis SSE
├── index.css        # Design system (Crystal theme)
├── pages/
│   ├── Login.jsx    # Login/Register con switcher
│   └── Confirm.jsx  # Confirmación de email
└── components/
    ├── Navbar.jsx   # Barra superior con dropdown perfil
    ├── Sidebar.jsx  # Sidebar izquierdo (solo desktop)
    ├── JobForm.jsx  # Formulario de oferta
    ├── DropZone.jsx # Zona de subida de CVs (drag & drop)
    ├── Results.jsx  # Tarjetas de resultados de candidatos
    └── Progress.jsx # Barra de progreso SSE
```

### Design System (Tailwind custom)
- **Theme**: Dark mode, Crystal glassmorphism
- **Colores principales**: Definidos en `tailwind.config.js`
  - `background`, `surface`, `on-surface`, `primary`, `outline-variant`, etc.
- **Componentes CSS**: `.crystal-card`, `.crystal-glass`, `.btn-primary`, `.btn-outline`, `.switcher`
- **Tipografía**: Inter (Google Fonts)

### DB Schema
- **users**: id, email, nombre, password_hash, confirmed, created_at
- **ofertas**: id, user_id (FK→users), descripcion, categoria, stack, created_at
- **candidatos**: id, oferta_id (FK→ofertas), filename, match_score, fortalezas, carencias, valoracion, recomendacion, email_candidato, telefono_candidato, created_at

## Estado Actual (Sprint 1 completado)
- ✅ Login/Register funcional con JWT
- ✅ Análisis de CVs con SSE streaming
- ✅ Match score semántico + análisis LLM
- ✅ Retry en error 429 de Groq con backoff
- ✅ Score pasado al LLM como guía flexible
- ✅ Fix doble scroll en móvil
- ✅ Popup dropdown en perfil (Navbar)
- ✅ Check verde limpio en login

## Reglas Importantes
1. NO usar IA local para el LLM (8GB RAM no da, y SentenceTransformer ya usa ~300MB)
2. Las variables de entorno en Coolify deben estar en "Production", NO "Preview"
3. El `.env` local tiene: GROQ_API_KEY, DATABASE_URL, SECRET_KEY, RESEND_API_KEY, VITE_API_URL
4. Resend free tier: solo envía al email verificado de la cuenta, necesita dominio verificado para otros
5. Los CVs se procesan con 1.5s de delay entre ellos para evitar rate limits de Groq
