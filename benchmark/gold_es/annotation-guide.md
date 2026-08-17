# Guía de anotación

## Qué se etiqueta

La unidad es la relación entre una vacante concreta y un CV concreto. No se puntúa el valor general de una persona ni se predice su contratación. La pregunta es: «con la evidencia escrita en este CV, ¿qué prioridad razonable tendría revisarlo para esta vacante?»

## Escala de relevancia

- `2` — ajuste fuerte: hay evidencia explícita de los criterios obligatorios evaluables y de la mayoría de los importantes. Los vacíos menores no cambian la prioridad alta.
- `1` — ajuste parcial: existe base profesional plausible, pero faltan, son parciales o quedan desconocidos uno o varios criterios relevantes. Merece revisión, no afirmación de idoneidad.
- `0` — no relevante para esta vacante: hay evidencia suficiente de desajuste profesional o incumplimiento claro de un criterio obligatorio evaluable. No se usa `0` solo porque el parser no encontró algo.
- `unknown` — no se puede decidir de forma fiable: documento ilegible/incompleto, evidencia insuficiente, criterio ambiguo o fallo de parsing que puede cambiar la conclusión.

`unknown` no equivale a `0`. Un requisito marcado como no evaluable en CV tampoco reduce la etiqueta.

## Estado por criterio

Cada criterio confirmado se anota además como:

- `confirmed`: evidencia directa suficiente.
- `partial`: evidencia relacionada pero incompleta.
- `not_found`: no se localizó evidencia; no demuestra ausencia.
- `contradictory`: el CV aporta evidencia incompatible con el requisito.
- `unknown`: el documento no permite evaluarlo.
- `not_evaluable`: debe verificarse por entrevista u otra fuente.

Toda decisión distinta de `not_found`, `unknown` o `not_evaluable` debe citar evidencia textual y, cuando exista, página/sección. No se infieren edad, género, origen, discapacidad, situación familiar ni otras características personales.

## Criterios confirmados antes del pool

Para cada vacante se conserva el texto original y una lista revisada de criterios:

- prioridad: `required`, `important`, `preferred` o `not_evaluable`;
- regla de evidencia: qué texto o experiencia basta para confirmarlo;
- equivalencias aceptadas en España;
- mínimo, cuando sea objetivo;
- política de dato no encontrado: `unknown` o revisión manual.

La persona que confirma criterios registra su identificador, fecha y versión. No debe ver resultados del motor.

## Negativos difíciles

Al menos el 30 % del pool debe ser difícil. Se marca uno o varios tipos:

- `adjacent_role`: profesión vecina y vocabulario parecido, pero funciones distintas;
- `missing_required`: perfil del área sin evidencia de un obligatorio central;
- `seniority_mismatch`: mismo campo con nivel de responsabilidad distinto;
- `sector_mismatch`: mismas herramientas o cargo en un contexto no transferible;
- `keyword_only`: cursos o palabras clave sin experiencia que las sostenga;
- `manager_vs_hands_on`: dirección frente a ejecución técnica, o al contrario;
- `near_positive`: cumple buena parte de los criterios, pero existe un motivo documentado para no asignar `2`.

Los negativos fáciles sirven para detectar fallos gruesos, pero no deben dominar las métricas.

## Doble revisión y adjudicación

1. Revisor A y revisor B trabajan independientemente sobre los mismos textos y criterios congelados.
2. Cada uno guarda su propio archivo compatible con `assessment.schema.json`, con `reviewer_id`, etiqueta, confianza, criterios, evidencias y notas.
3. No ven anotaciones del otro ni salidas de Malaquías antes de entregar.
4. Se envía a adjudicación cualquier desacuerdo de etiqueta, cualquier diferencia de dos niveles, toda confianza baja y una muestra del 10 % de acuerdos.
5. El adjudicador documenta la etiqueta final y el motivo usando `adjudication.schema.json`.
6. Se informa acuerdo exacto y acuerdo ponderado; no se ocultan discrepancias convirtiéndolas automáticamente en promedio.

Si aparece una ambigüedad sistemática, se corrige la guía, se incrementa la versión y se vuelve a revisar el lote afectado.

## Control por familia

- IT/datos: distinguir uso real de tecnologías frente a mera mención; comprobar funciones, nivel y actualidad sin fijar umbrales arbitrarios.
- Comercial/ventas: separar captación, gestión de cuentas, retail y dirección; no confundir sector con función comercial.
- Logística/almacén: separar almacén, tráfico, planificación y supervisión; licencias o disponibilidad no demostrables quedan `unknown`/`not_evaluable`.
