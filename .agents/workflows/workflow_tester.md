---
description: Agente QA — Tester automático de endpoints Malaquías contra entorno local
---

# Workflow: Tester QA Agent

Este workflow ejecuta pruebas automáticas contra el backend local de Malaquías.
**Prerrequisito**: `workflow_local_dev` debe haberse ejecutado antes. El backend debe estar en `http://localhost:8000`.

## Cuándo activar este agente
- Antes de hacer push a `main`
- Después de modificar `main.py`, `matcher.py`, `auth.py`, o `models.py`
- Antes de un redeploy en Coolify
- Después de ejecutar cualquier workflow de fase

## Paso 0 — Verificar que el backend local está arrancado

Ejecutar:
```bash
curl -s http://localhost:8000/health
```

Si no responde `{"status": "ok"}`, detener y ejecutar primero `workflow_local_dev`.

## Paso 1 — Preparar datos de test

El agente debe crear un archivo PDF de test mínimo si no existe en `benchmark/test_data/test_cv.pdf`.

Si no existe ningún PDF de test, buscar en `benchmark/` algún PDF existente para usarlo.
Si tampoco hay ninguno, avisar al usuario: "Necesito al menos un PDF de CV de prueba en benchmark/test_data/"

## Paso 2 — Test de autenticación (AUTH FLOW)

### 2.1 — Registro de usuario de test
```bash
curl -s -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "tester@malaquias.local", "password": "TestPass123!", "nombre": "Tester QA"}'
```
✅ Esperado: `{"message": "Cuenta creada exitosamente. Ya puedes iniciar sesión."}`
⚠️ Si devuelve "Email ya registrado", es OK, el usuario ya existe.

### 2.2 — Login y obtención de token
```bash
curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=tester@malaquias.local&password=TestPass123!"
```
✅ Esperado: JSON con `access_token`
❌ Si falla: reportar error crítico, el resto de tests no pueden ejecutarse.

**Guardar el token para los siguientes pasos** (variable `$TOKEN`).

### 2.3 — Verificar /me
```bash
curl -s http://localhost:8000/me \
  -H "Authorization: Bearer $TOKEN"
```
✅ Esperado: `{"email": "tester@malaquias.local", "nombre": "Tester QA"}`

## Paso 3 — Test del dashboard (datos frescos)
```bash
curl -s http://localhost:8000/dashboard \
  -H "Authorization: Bearer $TOKEN"
```
✅ Esperado: JSON con estructura `{total_ofertas, total_candidatos, score_promedio, distribucion, ultimos_candidatos}`
❌ Si falta cualquier campo: BUG — reportar.

## Paso 4 — Test del endpoint /analyze (core del motor)

Este es el test más importante. Usa un PDF real de `benchmark/`.

```bash
curl -s -X POST http://localhost:8000/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "job_description=Buscamos desarrollador Python con experiencia en FastAPI, SQLAlchemy y PostgreSQL. Valoramos conocimientos en Docker y CI/CD." \
  -F "strictness=normal" \
  -F "balance=0.5" \
  -F "cvs=@benchmark/test_data/test_cv.pdf;type=application/pdf"
```

**Interpretar SSE stream**:
- El stream debe abrir con `event: start`
- Por cada CV debe llegar `event: cv_done` con `result.match_score` (número 0-100)
- Cerrar con `event: complete`

✅ Criterios de éxito:
- `match_score` es un número entre 0 y 100
- `analysis` tiene al menos los campos: `fortalezas`, `carencias`, `valoracion`, `recomendacion`
- `nombre_candidato` y `titulo_candidato` no están vacíos
- No hay `"error"` en el resultado

⚠️ Criterios de advertencia (no críticos):
- `match_score` < 5: el scoring puede estar mal calibrado
- `recomendacion` no es "Entrevistar", "Considerar" o "Descartar": el LLM no siguió el schema

❌ Criterios de fallo crítico:
- La respuesta 401 o 422: problema de auth o validación
- El stream no cierra (timeout >30s): problema de streaming
- `analysis.error` presente: el LLM falló

## Paso 5 — Test de /save-analysis

Si el test anterior fue exitoso, hacer el save:
```bash
curl -s -X POST http://localhost:8000/save-analysis/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "descripcion": "Test QA - Python Developer",
    "categoria": "it_sistemas",
    "stack": "python",
    "balance": 0.5,
    "candidatos": [{
      "filename": "test_cv.pdf",
      "match_score": 72.5,
      "analysis": {
        "fortalezas": ["Experiencia en FastAPI", "Conoce PostgreSQL"],
        "carencias": ["Sin experiencia en Docker"],
        "valoracion": "Candidato sólido para el rol.",
        "recomendacion": "Entrevistar",
        "nombre_candidato": "Test Candidato",
        "titulo_candidato": "Python Developer",
        "email_candidato": "candidato@test.com",
        "telefono_candidato": null
      }
    }]
  }'
```
✅ Esperado: `{"status": "ok", "oferta_id": <número>}`

## Paso 6 — Test de /ofertas y /talent-pool
```bash
curl -s http://localhost:8000/ofertas \
  -H "Authorization: Bearer $TOKEN"
```
✅ Esperado: array con al menos 1 oferta (la del paso 5)

```bash
curl -s http://localhost:8000/talent-pool \
  -H "Authorization: Bearer $TOKEN"
```
✅ Esperado: array con al menos 1 candidato

## Paso 7 — Limpieza (reset datos de test)
```bash
curl -s -X DELETE http://localhost:8000/reset-data \
  -H "Authorization: Bearer $TOKEN"
```
✅ Esperado: `{"message": "Todos tus datos han sido eliminados correctamente"}`

## Paso 8 — Generar reporte de QA

Presentar el resultado en este formato:

```
## 🧪 Reporte QA — Malaquías — [fecha y hora]

### ✅ Tests pasados
- [lista de tests exitosos]

### ❌ Tests fallidos (CRÍTICOS)
- [lista de fallos críticos con detalle del error]

### ⚠️ Advertencias
- [lista de comportamientos inesperados pero no bloqueantes]

### 🎯 Score QA: X/8 tests pasados

### 📋 Veredicto
- VERDE: 7–8/8 → Listo para deploy
- AMARILLO: 5–6/8 → Revisar advertencias antes de deploy  
- ROJO: <5/8 → NO hacer deploy, hay bugs críticos

### 🔧 Recomendaciones
- [acciones concretas para resolver los fallos]
```

## Notas importantes
- El agente NO modifica código, solo ejecuta tests y reporta
- Si el backend no está levantado, NO intentar levantarlo (ese es el trabajo de `workflow_local_dev`)
- Los datos de test se limpian al final, no contaminar la base de datos
- Si hay errores de CORS en los tests de curl, ignorar (solo afecta al browser)
- El test del `/analyze` puede tardar 10-30 segundos por la carga del modelo sentence-transformers en la primera ejecución
