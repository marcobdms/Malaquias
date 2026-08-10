# Sistema visual de Malaquías

Este documento formaliza los patrones que ya existen en el frontend. No cambia la marca: convierte el lenguaje visual actual en reglas reutilizables para que las nuevas pantallas mantengan coherencia.

## Principios de producto

1. **Evidencia antes que afirmaciones.** Un resultado explica qué se encontró, dónde y qué información sigue siendo desconocida.
2. **El índice es contextual.** Ordena candidatos dentro de una vacante; no expresa probabilidad de contratación ni calidad humana absoluta.
3. **No encontrado no significa que no exista.** La interfaz usa `desconocido` o `requiere revisión` cuando el CV no permite comprobar algo.
4. **El usuario confirma la vacante.** Los criterios que afectan al ranking deben ser visibles y editables.
5. **La complejidad técnica vive en el laboratorio.** Balance semántico, pesos internos y severidad no son controles principales para un reclutador.

## Identidad observada

- Fondo negro (`#0a0a0a`) y superficies gris oscuro.
- Inter, títulos pesados y etiquetas pequeñas en mayúsculas.
- Tarjetas amplias, radios generosos y bordes de bajo contraste.
- Acciones principales blancas con forma de píldora.
- Material Symbols como familia de iconos.
- Navegación lateral en escritorio e inferior en móvil.
- Vista dividida entre entrada y resultados en pantallas grandes.

Los tokens canónicos viven en `frontend/tailwind.config.js`; no se duplica un valor si ya existe un token equivalente.

## Jerarquía de superficies

| Nivel | Token | Uso |
| --- | --- | --- |
| Fondo | `background` | Lienzo general |
| Base | `surface` | Tarjetas principales |
| Baja | `surface-container-low` | Paneles secundarios |
| Media | `surface-container` | Campos, filas y estados |
| Alta | `surface-container-high` | Selección y elementos destacados |

La separación se consigue primero con superficie, borde y espacio. Las sombras y desenfoques no compiten con el contenido.

## Patrones de componentes

### Vacante

- Cada campo tiene etiqueta visible y asociada.
- La descripción original se conserva.
- Los criterios se agrupan en `obligatorio`, `importante`, `deseable` y `no evaluable en CV`.
- Los errores aparecen junto al campo; la acción principal no queda deshabilitada sin explicación.

### Documentos

Cada archivo podrá evolucionar hacia: listo, advertencia de lectura, requiere OCR, duplicado, protegido, vacío o error recuperable. Estado, icono y texto aparecen juntos; el color nunca es la única señal.

### Candidato

El encabezado usa `Primero en esta evaluación`, no `Mejor candidato`. El número principal se denomina `Índice de prioridad`. La tarjeta separará progresivamente:

- Índice de alineación.
- Confianza o cobertura de información.
- Obligatorios confirmados, parciales y desconocidos.
- Evidencia textual y página de origen.
- Problemas de lectura.

### Progreso

Las fases describen trabajo comprensible: preparar documentos, leer CV, evaluar criterios y ordenar resultados. Los cambios se anuncian con `aria-live="polite"`.

## Accesibilidad y respuesta adaptable

- Objetivos táctiles mínimos de 44 × 44 px y foco visible.
- Elementos HTML nativos para botones, campos y navegación.
- Contraste AA y texto/icono además de color para estados.
- Respeto por `prefers-reduced-motion`.
- Sin desplazamiento horizontal a 320 px.
- En móvil, flujo vertical y resultados desplegables; no tablas anchas.
- El documento HTML se declara en español.

## Vocabulario

| Evitar | Usar |
| --- | --- |
| Mejor candidato | Primero en esta evaluación |
| Compatibilidad 82 % | Índice de prioridad 82/100 |
| No tiene | No encontrado en el CV |
| Carencias | Aspectos por verificar |
| Despertando motor neuronal | Preparando el análisis |
| Descartar automáticamente | Requiere revisión / alineación limitada |

## Secuencia prevista

1. Pegar y revisar la vacante.
2. Confirmar criterios evaluables en un CV.
3. Cargar y comprobar documentos.
4. Confirmar el alcance del análisis.
5. Seguir el progreso.
6. Revisar ranking, desconocidos y evidencias.

Las ampliaciones reutilizan `crystal-card`, `btn-primary`, `btn-outline`, los tokens de Tailwind y la navegación existente antes de crear variantes.
