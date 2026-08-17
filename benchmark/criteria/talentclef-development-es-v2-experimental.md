# Catálogo de criterios TalentCLEF ES v2 (experimental)

Este catálogo es una capa de calibración. No sustituye v1, no modifica las etiquetas de TalentCLEF y no debe usarse en producción antes de completar la ablación.

## Trazabilidad

- Fuente: `benchmark/criteria/talentclef-development-es-v1.json`.
- SHA-256 de v1: `3fc5eee6c4eb3793092743630ae5b6bf391fb28f5466c0eda84117df60290511`.
- Cobertura preservada: 10 ofertas y 75 criterios.
- Se conservan en el mismo orden los `query_id`, `id`, prioridades y `job_text_sha256`.
- Los cuatro criterios `not_evaluable` permanecen para trazabilidad, pero llevan `anchor_terms: []` y deben quedar fuera del scoring automático.

## Decisiones de v2

1. Cada criterio evaluable incorpora `anchor_terms` respaldados por su descripción y evidencia esperada en v1.
2. Las equivalencias siguen siendo alternativas OR. Se han concretado con el dominio del puesto para impedir que palabras transversales como “análisis”, “gestión”, “datos”, “documentación” o “equipo” confirmen solas un criterio.
3. Los criterios inherentemente amplios no se eliminan: llevan `experimental_note` y exigen contexto del dominio. Esto conserva el significado de la oferta sin fingir que el criterio discrimina por sí solo.
4. En `96027-failure-root-cause` se añaden explícitamente `FMEA`, `AMFE`, `análisis de modo de falla y efectos` y `análisis modal de fallos y efectos`. La inclusión corrige el vocabulario incompleto observado en revisión y no crea un requisito nuevo: son técnicas y expresiones del mismo concepto de análisis de fallas/causa raíz.
5. No se añadieron titulaciones, años de experiencia, herramientas, normativas o certificaciones que no estuvieran recogidas en v1 y su oferta fuente.

## Criterios amplios señalados

Se marcan, entre otros, comunicación de equipo en caja, documentación técnica, gestión de aula, seguridad en limpieza, documentación de privacidad, interpretación de datos de fallas, trazabilidad y liderazgo de proyectos de datos. La nota no cambia su prioridad ni su pertenencia a la oferta; únicamente evita tratarlos como evidencia autosuficiente.

## Validación prevista

La comparación debe separar cuatro efectos sobre exactamente los mismos pools: criterios v1/fórmula v1, criterios v2/fórmula v1, criterios v1/matcher léxico v2 y criterios v2/matcher léxico v2. La decisión debe observar ranking, falsos positivos en obligatorios, falsos negativos conocidos y saturación por criterio. TalentCLEF sigue siendo una señal auxiliar: sus candidatos no marcados no equivalen automáticamente a negativos humanos confirmados.
