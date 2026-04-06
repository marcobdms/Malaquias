---
description: Manager Agent — Orquestador de sesión y resumen de cambios
---

# Manager Agent — Orquestador de Sesión

Este workflow se ejecuta **al final de cada sesión de trabajo** o cuando el usuario escribe `/manager`.
Su función es actuar como un agente observador que consolida todo lo que ha pasado en la sesión y entrega un resumen estructurado.

## Cuándo activarlo

- Al final de una sesión larga de cambios
- Cuando quieras un resumen de lo que se hizo antes de hacer commit
- Cuando varios workflows se hayan ejecutado en secuencia y quieras consolidar

## Instrucciones para el agente

### Paso 1 — Leer contexto base
Lee siempre primero:
- `CLAUDE.md` (estado del proyecto)
- `.agents/workflows/` (qué workflows existen)

### Paso 2 — Detectar cambios de la sesión
Ejecuta este comando para ver qué archivos cambiaron:
```bash
git diff --stat HEAD
git status --short
```

Si hay cambios staged:
```bash
git diff --cached --stat
```

### Paso 3 — Analizar cambios por área
Para cada archivo modificado, determina:
- **Backend** (`backend/app/`): cambios en lógica, endpoints, modelos
- **Frontend** (`frontend/src/`): cambios en UI, componentes, estado
- **Infraestructura** (`.env`, `docker-compose`, requirements): cambios de config
- **Tests/Benchmark** (`benchmark/`): cambios en datos o scripts de evaluación
- **Agentes** (`.agents/`): cambios en workflows o reglas

### Paso 4 — Generar resumen estructurado
Presenta el resumen en este formato exacto:

```
## 📋 Resumen de Sesión — [fecha]

### ✅ Cambios implementados
- [archivo]: [qué hizo]
- [archivo]: [qué hizo]

### 🧠 Decisiones técnicas tomadas
- [decisión] → [razón]

### ⚠️ Pendientes detectados
- [cosa que quedó a medias o genera deuda técnica]

### 🔗 Impacto en producción
- Backend Coolify: [afecta / no afecta / requiere redeploy]
- Frontend Vercel: [afecta / no afecta / requiere redeploy]
- Base de datos Supabase: [hay migraciones pendientes / sin cambios]

### 🧪 Estado QA
- [tests ejecutados / no ejecutados]
- Si no se ejecutó el tester: "⚠ Recomienda ejecutar /tester antes del deploy"

### 📦 Commit sugerido
[tipo]: [descripción en inglés, estilo conventional commits]
Ejemplo: feat(matcher): add bigram support to keyword_score
```

### Paso 5 — Preguntar si proceder
Después de mostrar el resumen, pregunta:
> "¿Quieres que genere el commit con este mensaje, ejecute el tester, o hay algo que corregir?"

## Notas
- No modifica ningún archivo, solo lee y reporta
- Si detecta migraciones de base de datos pendientes, marcar siempre como CRÍTICO
- Si hay cambios en `requirements.txt` o `package.json`, recordar redeploy en Coolify/Vercel
- Si se modificó `main.py` o `matcher.py`, recomendar SIEMPRE ejecutar el tester
