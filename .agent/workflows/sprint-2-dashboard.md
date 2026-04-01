---
description: Sprint 2 - Dashboard con métricas, sidebar funcional, posiciones abiertas e historial
---

# Sprint 2 — Dashboard Básico

## Prerrequisito
Lee primero `/project-context` para entender el proyecto completo.

## Tareas

### 1. Sidebar funcional con navegación
- **Archivo**: `frontend/src/components/Sidebar.jsx` + `frontend/src/App.jsx`
- Convertir el sidebar estático en un sistema de navegación basado en estado
- Secciones: Dashboard, Nuevo Análisis, Posiciones Abiertas, (futuro: Talent Pool, Reports)
- En móvil: usar la barra inferior existente o un menú hamburguesa
- El Sidebar ya existe con un diseño Crystal, mantener el estilo actual

### 2. Dashboard con métricas desde la DB
- **Backend**: Crear endpoint `GET /dashboard` en `main.py` que devuelva:
  - Total de CVs analizados (candidatos)
  - Total de posiciones (ofertas)
  - Distribución de recomendaciones (Entrevistar/Considerar/Descartar en %)
  - Últimos 5 candidatos analizados
  - Score promedio
- **Frontend**: Crear componente `Dashboard.jsx` en `frontend/src/components/`
  - Tarjetas de métricas con iconos y animaciones
  - Gráfico de distribución (puede ser un donut simple con CSS o SVG, sin librerías externas)
  - Lista de últimos candidatos
  - Mantener estilo Crystal (dark mode, glassmorphism)

### 3. Lista de Posiciones Abiertas
- **Backend**: Crear endpoint `GET /ofertas` que devuelva todas las ofertas del usuario con count de candidatos
- **Frontend**: Crear componente `Positions.jsx`
  - Lista de ofertas con: descripción truncada, categoría, stack, fecha, # de candidatos
  - Click para ver los candidatos de esa oferta
- **Backend**: Crear endpoint `GET /ofertas/{id}/candidatos` que devuelva los candidatos de una oferta

### 4. Historial de análisis
- Integrado en la vista de Posiciones (ver candidatos de una oferta pasada)
- Reutilizar el componente `Results.jsx` existente para mostrar candidatos históricos

### 5. Explorar alternativas a Resend
- Investigar: verificar dominio en Resend vs usar otra opción
- Opciones: Resend con dominio, Mailgun free tier, o desactivar temporalmente la confirmación por email
- Decisión a tomar con el usuario

## Reglas
- NO tocar `matcher.py` ni `llm.py` (eso es Sprint 4)
- NO implementar OAuth (eso es Sprint 3)
- Mantener el design system Crystal existente
- Usar Tailwind classes consistentes con el resto del proyecto
- Backend endpoints deben requerir autenticación (`Depends(get_current_user)`)
