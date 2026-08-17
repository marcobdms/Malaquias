# Paquete de revisión humana

Convierte un run del benchmark en un material que una persona pueda revisar sin
abrir los CV originales. Admite dos formatos existentes:

- `benchmark/results/runs/.../result.json`: benchmark matemático multivacante.
- `benchmark/results/manual_cases/.../engine_result.json`: prueba completa por API/UI.

Genera tres archivos:

- `review.md`: vacante, ranking, componentes y evidencia profesional anonimizada.
- `review_package.json`: la misma información en formato estructurado.
- `review_form.json`: formulario para marcar `0=no encaja`, `1=dudoso` o `2=encaja`.

## Uso

Desde la raíz del proyecto:

```powershell
python benchmark/review/generate.py `
  --run benchmark/results/runs/20260812T125008Z-da675d88e6/result.json `
  --output benchmark/results/reviews/20260812T125008Z-da675d88e6 `
  --top 10 `
  --errors 5
```

Para revisar solo una vacante, añade `--query 75767`. La opción puede repetirse.
Si el run se movió de equipo y su `source_root` absoluto ya no existe, usa:

```powershell
python benchmark/review/generate.py `
  --run RUTA_AL_RESULTADO `
  --output RUTA_DE_SALIDA `
  --source-root benchmark/data/downloaded/talentclef_2026_task_a/extracted/TaskA/development/es
```

El resultado es reproducible: con el mismo run y opciones se obtiene el mismo
contenido. Los alias anónimos se derivan del run, la vacante y el candidato. En
los casos manuales, el generador enlaza cada fila con `ground_truth.json` y busca
primero el perfil de texto del corpus TalentCLEF. Si no está disponible, intenta
el PDF relacionado dentro de `cvs/` usando `pypdf`, ya incluido por el backend.

## Qué significa acierto o error

El corte `--top N` representa la decisión operacional de revisar los primeros N:

- relevante dentro del top N: `acierto_positivo`;
- no relevante dentro del top N: `falso_positivo`;
- relevante fuera del top N: `falso_negativo`;
- no relevante fuera del top N: `acierto_negativo`.

La etiqueta del dataset no se considera verdad perfecta. Precisamente por eso el
formulario humano usa una escala 0/1/2 y permite explicar desacuerdos.

## Privacidad y límites

El paquete no guarda el ID original, nombre, correo, teléfono, URL ni cabecera del
CV. De los corpus de texto toma únicamente viñetas profesionales y líneas de
habilidades/certificaciones, aplicando además redacción por patrones. Esta medida
reduce identificadores directos, pero no sustituye una anonimización jurídica de
CV privados; este flujo se ha diseñado para datasets públicos/sintéticos.

Los criterios guardados dentro de `score_components.criteria` se muestran con su
score, componentes semántico/keyword, prioridad y estado. También se conservan los
tiempos generales del run y tiempos por candidato cuando existen.

Los runs antiguos no contienen todos los diagnósticos nuevos. Si faltan el estado
de elegibilidad, la cobertura de requisitos o los componentes del score, el
paquete muestra `no disponible`; nunca los reconstruye ni los inventa. El run
matemático tampoco contiene análisis Gemini. El run API puede aportar evidencia
desde fortalezas/carencias, pero normalmente no conserva semantic/keyword.
