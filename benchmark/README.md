# Benchmark v2

Este laboratorio empieza desde cero. No reutiliza los CV, rutas ni rankings del benchmark histórico de `malaquias-pro-v1.5`.

## Qué mide

El benchmark separa tres preguntas que antes estaban mezcladas:

1. **Lectura:** ¿el documento se convirtió en texto y hechos correctos?
2. **Interpretación:** ¿se relacionaron esos hechos con los criterios adecuados?
3. **Ranking:** ¿el orden resultante se parece al orden de referencia?

Un fallo de lectura no debe registrarse como un candidato inadecuado. Un dato no encontrado se etiqueta como `unknown`, no como ausencia demostrada.

## Estructura local

```text
benchmark/
  schemas/                 contratos JSON versionados
  scripts/                 herramientas reproducibles
  sources.json             procedencia y finalidad de cada corpus
  data/
    downloaded/            descargas públicas, ignoradas por Git
    private/               corpus aportado por cada usuario, ignorado por Git
  results/                 ejecuciones locales, ignoradas por Git
```

Los datasets grandes no se redistribuyen desde este repositorio. `sources.json` conserva URL, licencia, idioma y finalidad, y `scripts/fetch_sources.py` descarga únicamente las fuentes marcadas como automáticas.

## Conjuntos

- `calibration`: casos visibles utilizados para ajustar reglas, pesos o prompts.
- `holdout`: examen cerrado; no se usa mientras se ajusta el motor.
- `parser`: documento y representación correcta esperada.
- `ranking`: vacante, pool de candidatos y relevancia revisada.

No se publica un resultado agregado que mezcle parser y ranking. Tampoco se mezclan corpus auxiliares extranjeros con el futuro núcleo español.

## Fuentes iniciales

- Vacantes abiertas españolas: ECYL, Xunta de Galicia, Feina Activa y Lorca.
- Ranking auxiliar en español: TalentCLEF 2026.
- Parser auxiliar: Resume Dataset / LiveCareer, sujeto a revisar su procedencia antes de utilizarlo.
- Normalización: ESCO, CNO-11 e INCUAL.

## Descargar fuentes abiertas

Desde la raíz:

```powershell
python benchmark/scripts/fetch_sources.py --list
python benchmark/scripts/fetch_sources.py ecyl
```

Cada descarga se guarda con fecha, hash SHA-256 y una copia del metadato de origen. El contenido descargado no se incluye en Git.

## Añadir un corpus propio

Guarda los documentos en `benchmark/data/private/` y usa identificadores anónimos. Para ranking, cada caso necesita una vacante, candidatos del pool completo y una etiqueta `0`, `1`, `2` o `unknown`. Reserva una parte para `holdout` antes de comenzar a ajustar.

Los esquemas de `benchmark/schemas/` son el contrato compartido por importadores, anotadores y el futuro evaluador.

## Runner reproducible de ranking

El runner de `benchmark/runner.py` evalua unicamente el ranking matematico. No
arranca FastAPI, no genera explicaciones y no llama a Gemini ni a ningun
otro LLM. La configuracion baseline replica el enfoque hibrido actual:
SentenceTransformer, coincidencia de palabras y ajuste de severidad.

Primero descarga y extrae TalentCLEF en la ruta declarada por el manifiesto.
La descarga permanece ignorada por Git. Despues ejecuta, desde la raiz:

```powershell
.\.venv\Scripts\python.exe -m benchmark.runner `
  --manifest benchmark/manifests/talentclef-development-es.json `
  --config benchmark/configs/baseline.json
```

`--max-queries 1` permite un smoke test, pero queda registrado en el resultado
y no debe publicarse como benchmark completo. Cada ejecucion escribe en
`benchmark/results/runs/<run-id>/`:

- `result.json`: commit y estado de Git, seed, parametros, hashes de
  manifiesto/config/dataset, ranking y componentes del score de cada candidato.
- `summary.md`: P@k, Recall@k, MRR y nDCG@k agregados.

Los embeddings se guardan en
`benchmark/results/cache/embeddings.sqlite3`. La clave combina modelo y hash del
texto, de modo que cambiar el modelo o el documento invalida solamente la
entrada afectada.

Para comparar una configuracion nueva con un resultado congelado:

```powershell
.\.venv\Scripts\python.exe -m benchmark.runner `
  --manifest benchmark/manifests/talentclef-development-es.json `
  --config benchmark/configs/mi-experimento.json `
  --baseline benchmark/results/runs/<baseline>/result.json
```

La comparacion registra deltas; nunca modifica automaticamente los pesos del
motor. Copia `baseline.json` con otro nombre para cada experimento, cambia una
variable cada vez y conserva la seed.

### Ejecutar en segundo plano

En Windows se puede dejar el calculo corriendo mientras se trabaja en otra
tarea. Los logs y resultados quedan en el directorio ignorado:

```powershell
$log = "benchmark/results/background"
New-Item -ItemType Directory -Force $log | Out-Null
Start-Process -FilePath ".\.venv\Scripts\python.exe" `
  -ArgumentList @(
    "-m", "benchmark.runner",
    "--manifest", "benchmark/manifests/talentclef-development-es.json",
    "--config", "benchmark/configs/baseline.json"
  ) `
  -RedirectStandardOutput "$log/stdout.log" `
  -RedirectStandardError "$log/stderr.log" `
  -WindowStyle Hidden -PassThru
```

El PID devuelto permite comprobar el proceso con `Get-Process -Id <PID>`. No
ejecutes dos procesos con la misma carpeta de salida mientras se esta creando
el primer cache.

### Manifiestos de pools

`benchmark/manifests/` versiona que queries, corpus, qrels y estrategia de pool
forman una prueba. TalentCLEF admite:

- `all`: todos los perfiles del corpus; es el benchmark recomendado.
- `judged`: solo candidatos presentes en qrels; util para depurar loaders.
- `positives_plus_sampled_negatives`: positivos y una muestra reproducible de
  negativos definida por `negatives_per_query` y la seed de la configuracion.

En TalentCLEF, los perfiles ausentes de qrels se interpretan como no
relevantes. Esta convencion no debe trasladarse sin revision al futuro gold set
espanol, donde `unknown` se excluye de las metricas.

## Tests del laboratorio

Las pruebas no descargan modelos ni datos externos:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s benchmark/tests -v
```

## Grid de calibración matemática

Las configuraciones `chunked-*-v2.json` leen el CV por fragmentos de 96 tokens
con solape. Así el contenido situado después del límite de 128 tokens de MiniLM
no desaparece del componente semántico. El grid compara cinco balances sin usar
Gemini y reutiliza el mismo modelo y caché:

```powershell
python -m benchmark.scripts.run_grid `
  --manifest benchmark/manifests/talentclef-development-es.json `
  --configs benchmark/configs/chunked-*-v2.json
```

Cada matriz queda en `benchmark/results/grids/<grid-id>/`. La selección debe
mirar al menos `nDCG@5`, `nDCG@10`, precisión y recall; no se cambia producción
por una única métrica agregada.

El manifiesto `talentclef-hard-negatives-es.json` usa un pool de estrés
congelado. Sus negativos fueron seleccionados por el baseline y por eso sirve
para comparar errores cercanos, no como resultado imparcial ni como holdout.

## Catálogo de vacantes españolas

`benchmark/catalogs/ecyl-pilot-selection.json` selecciona nueve ofertas reales
del snapshot público ECYL. Para reconstruir el catálogo normalizado:

```powershell
python benchmark/scripts/prepare_ecyl_catalog.py `
  --selection benchmark/catalogs/ecyl-pilot-selection.json `
  --output benchmark/catalogs/ecyl-pilot-jobs.json
```

Estas ofertas tienen fuente, fecha, licencia y hash. Su estado es
`input_only_unjudged`: permiten diseñar criterios y pools españoles, pero no
aportan métricas hasta asociarlas a CV y relevancias revisadas por personas.
