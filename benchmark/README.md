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
