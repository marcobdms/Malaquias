# Gold set español de Malaquías

Esta carpeta define el contrato y el proceso de anotación del futuro gold set español. No contiene CV ni vacantes inventados. Los documentos solo se incorporan cuando existe una fuente identificable y un registro de procedencia.

## Objetivo del piloto

El piloto inicial tendrá 15 vacantes españolas y entre 25 y 40 CV por vacante:

| Familia | Vacantes piloto | Expansión | Perfiles orientativos |
| --- | ---: | ---: | --- |
| IT y datos | 5 | 10 | desarrollo, soporte, sistemas, datos, ciberseguridad |
| Comercial y ventas | 5 | 10 | SDR, account manager, retail, ventas B2B, dirección comercial |
| Logística y almacén | 5 | 10 | mozo/a, carretilla, tráfico, planificación, responsable de almacén |

La expansión prevista es de 30 vacantes. Para el piloto se congelan 12 vacantes en `calibration` y 3 en `holdout`; el reparto se realiza por vacante completa, nunca por pares aislados, antes de calibrar el motor.

## Estructura

```text
gold_es/
  manifest.json                    alcance y estado del conjunto
  annotation-guide.md              reglas humanas de etiquetado
  schemas/                         contratos propios del gold set
  templates/                       ejemplos vacíos, sin datos ficticios
  calibration/                     referencias visibles durante el ajuste
  holdout/                         referencias selladas hasta evaluación final
  incoming/                        material pendiente de licencia y revisión
```

Los objetos de vacante y evaluación siguen `benchmark/schemas/job.schema.json` y `benchmark/schemas/assessment.schema.json`. Los esquemas de esta carpeta solo añaden agrupación del pool, procedencia y adjudicación; no cambian el contrato del motor.

Los documentos originales no se versionan aquí. Deben guardarse bajo `benchmark/data/private/` o `benchmark/data/downloaded/`, usando identificadores anónimos. El gold set contiene únicamente manifiestos, hashes, referencias y anotaciones que puedan publicarse.

## Flujo de incorporación

1. Registrar cada vacante o CV en un `source-record` con URL u origen, fecha, hash y licencia/permiso.
2. Si la licencia o el permiso no están claros, dejar el elemento en `incoming` con estado `quarantine`; no se usa ni redistribuye.
3. Normalizar la vacante con el esquema `job.schema.json`.
4. Confirmar sus criterios con una persona conocedora del puesto antes de mirar scores o construir el pool.
5. Formar un pool con positivos plausibles, perfiles parciales, negativos fáciles y al menos un 30 % de negativos difíciles.
6. Asignar la vacante completa a `calibration` o `holdout` y congelar el reparto.
7. Dos revisores etiquetan cada relación de forma independiente y sin ver el score de Malaquías.
8. Un tercer revisor adjudica desacuerdos. Solo la adjudicación pasa a ser referencia final.
9. Ejecutar calibración únicamente sobre `calibration`. Abrir `holdout` cuando haya una versión candidata cerrada.

## Regla de no fuga

- No se cambian criterios después de revisar candidatos, salvo corrección documentada y nueva versión del caso.
- No se ajustan pesos, prompts ni umbrales mirando `holdout`.
- Siempre que sea posible, un candidato no aparece en ambos splits. Si se reutiliza, debe declararse en el manifiesto y excluirse de métricas sensibles a fuga.
- Los revisores no ven ranking, score ni explicaciones del motor.

## Cuándo el gold set es utilizable

El piloto no se considera gold hasta que tenga procedencia completa, criterios confirmados, pools cerrados, doble revisión, adjudicación y el holdout sellado. Antes de eso su estado es `draft`.
