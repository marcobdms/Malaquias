---
description: Configurar entorno local de desarrollo para poder ejecutar el tester QA
---

# Workflow: Local Dev Setup

Este workflow configura Malaquías para correr **localmente** en modo desarrollo, desacoplado de Vercel y Coolify.
Es el **prerrequisito obligatorio** antes de ejecutar el tester QA (`/tester`).

## Contexto
El stack productivo usa Vercel + Coolify + Supabase. Para QA local:
- Backend FastAPI corre en `http://localhost:8000`
- Frontend Vite corre en `http://localhost:5173`
- Base de datos: SQLite local (o Supabase con credenciales reales desde `.env`)
- Groq API: se usa la key real del `.env` (es barata, no hay problema)

## Prerrequisitos del sistema
- Python 3.12 instalado
- Node.js 18+ instalado
- pip instalado

## Paso 1 — Verificar que existe `.env` en backend

Lee `backend/.env` y verifica que tiene estas variables:
- `GROQ_API_KEY` ✓
- `DATABASE_URL` (puede ser Supabase o SQLite local)
- `SECRET_KEY`
- `RESEND_API_KEY` (para tests de email, puede ser dummy)
- `FRONTEND_URL=http://localhost:5173`

Si falta `DATABASE_URL`, crear versión SQLite:
```
DATABASE_URL=sqlite:///./malaquias_local.db
```

## Paso 2 — Crear entorno virtual Python (si no existe)

```bash
cd backend
python -m venv .venv
```

Activar en Windows:
```bash
.venv\Scripts\activate
```

## Paso 3 — Instalar dependencias Python

```bash
pip install -r requirements.txt
```

Si no existe `requirements.txt`, generarlo con los imports detectados en `backend/app/`:
```
fastapi
uvicorn
python-multipart
sentence-transformers
groq
sqlalchemy
pypdf
python-jose[cryptography]
passlib[bcrypt]
resend
httpx
pytest
pytest-asyncio
httpx
```

## Paso 4 — Arrancar backend local

// turbo
```bash
cd backend && .venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Verificar que responde:
```bash
curl http://localhost:8000/health
```
Debe devolver: `{"status": "ok"}`

## Paso 5 — Instalar dependencias frontend

```bash
cd frontend && npm install
```

## Paso 6 — Configurar frontend para apuntar a local

Verificar que `frontend/.env.local` existe con:
```
VITE_API_URL=http://localhost:8000
```

Si no existe, crearlo.

## Paso 7 — Arrancar frontend local

```bash
cd frontend && npm run dev
```

Frontend disponible en `http://localhost:5173`

## Verificación final

El entorno local está listo cuando:
- ✅ `http://localhost:8000/health` → `{"status": "ok"}`
- ✅ `http://localhost:5173` → muestra la UI de Malaquías
- ✅ No hay errores de CORS en la consola del browser

## Notas importantes
- El modelo sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) se descarga automáticamente en la primera ejecución (~500MB). Puede tardar.
- Si usas SQLite en vez de Supabase, las tablas se crean automáticamente en el primer arranque gracias a SQLAlchemy.
- El frontend en producción apunta a Coolify (`VITE_API_URL` en Vercel). Localmente apunta a `localhost:8000`. No hay que tocar el código.
