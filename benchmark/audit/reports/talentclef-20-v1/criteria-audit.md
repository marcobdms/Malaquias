# Auditoría reproducible de criterios

Fuente: `C:\Users\Marco\Desktop\proyectos\malaquias\benchmark\results\manual_suites\talentclef-20-v1`

Esta auditoría reutiliza resultados ya generados. No ejecuta Gemini, parsing de PDF ni scoring.
TalentCLEF se usa como señal auxiliar: una discrepancia con sus etiquetas no demuestra por sí sola un error del motor.

## Resumen por configuración

| Configuración | Casos | Criterios | Saturación media | Saturados 100% | Saturados >=80% | Marcados no discriminantes | AUC híbrida media | Evidencia persistida |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| kw1.0 | 10 | 71 | 22.5% | 0 | 2 | 19 | 0.680 | 0 |
| kw2.5 | 10 | 71 | 78.4% | 14 | 46 | 51 | 0.708 | 0 |

## Lectura principal

Al pasar de `kw1.0` a `kw2.5`, la saturación léxica media cambia de 22.5% a 78.4% (+55.8%).
Los criterios saturados en al menos el 80% del pool pasan de 2 a 46.
`no discriminante` es una alerta de auditoría, no una sentencia: combina saturación, varianza, separación de etiquetas y AUC, y debe revisarse con criterio humano.
Este suite no guardó fragmentos de evidencia por criterio; sí conserva posición y candidato. El JSON registra `evidence_available=false` para hacerlo explícito.

## Criterios señalados con kw2.5

| Caso | Criterio | Prioridad | Saturación | Gap +/− | AUC | Confirmados | Motivos |
|---|---|---|---:|---:|---:|---:|---|
| talentclef-91821-20 | Investigación jurídica y seguimiento regulatorio | required | 100% | +0.004 | 0.430 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-96356-20 | Traducción de casos de uso y liderazgo de proyectos de datos | important | 100% | +0.004 | 0.570 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-91821-20 | Gobernanza y ciclo de vida de la información | required | 100% | +0.007 | 0.620 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-90596-20 | Eficiencia energética y sistemas de gestión ambiental | important | 100% | -0.010 | 0.530 | 100% | keyword_saturation_gte_80pct, hybrid_label_gap_below_0.03, hybrid_auc_near_random |
| talentclef-87280-20 | Seguimiento de procedimientos de seguridad y reporte de incidencias | important | 100% | -0.011 | 0.470 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03, hybrid_auc_near_random |
| talentclef-76474-20 | Comunicación profesional y trabajo en equipo | important | 100% | +0.013 | 0.670 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-91821-20 | Documentación para auditorías, incidentes y gestión de registros | important | 100% | +0.016 | 0.690 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-90596-20 | Gestión de proveedores, contratos y equipos internos | required | 100% | +0.027 | 0.780 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-88540-20 | Liderazgo y gestión de equipos de ventas | required | 100% | +0.033 | 0.930 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance |
| talentclef-87280-20 | Limpieza profesional o mantenimiento doméstico | required | 100% | +0.038 | 0.870 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance |
| talentclef-91821-20 | Programas de privacidad y protección de datos | required | 100% | -0.043 | 0.120 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance |
| talentclef-90596-20 | Seguridad y cumplimiento normativo de instalaciones | required | 100% | +0.050 | 0.860 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance |
| talentclef-86302-20 | Diseño curricular y adaptación de planes de clase | important | 100% | +0.072 | 0.729 | 100% | keyword_saturation_gte_80pct |
| talentclef-96356-20 | Modelado de datos, pipelines y procesos ETL | required | 100% | +0.094 | 0.970 | 100% | keyword_saturation_gte_80pct |
| talentclef-75767-20 | Cálculos y entregables de diseño mecánico detallado | important | 95% | +0.028 | 0.520 | 95% | keyword_saturation_gte_80pct, hybrid_label_gap_below_0.03, hybrid_auc_near_random |
| talentclef-90596-20 | Gestión de proyectos de mejoras y renovaciones | important | 95% | -0.033 | 0.440 | 95% | keyword_saturation_gte_80pct |
| talentclef-96356-20 | Calidad, gobernanza y cumplimiento de estándares de datos | required | 95% | +0.035 | 0.850 | 100% | keyword_saturation_gte_80pct |
| talentclef-96027-20 | Interpretación de datos e informes técnicos | required | 95% | -0.047 | 0.500 | 95% | keyword_saturation_gte_80pct, hybrid_auc_near_random |
| talentclef-86302-20 | Gestión del aula y estrategias pedagógicas | required | 95% | +0.060 | 0.708 | 95% | keyword_saturation_gte_80pct |
| talentclef-91821-20 | Asistencia legal o apoyo a un departamento jurídico | required | 95% | +0.081 | 0.800 | 95% | keyword_saturation_gte_80pct |
| talentclef-75767-20 | Diseño y optimización de sistemas HVAC | required | 95% | +0.088 | 0.790 | 95% | keyword_saturation_gte_80pct |
| talentclef-87280-20 | Limpieza, desinfección y estándares de higiene | required | 95% | +0.103 | 0.920 | 95% | keyword_saturation_gte_80pct |
| talentclef-90596-20 | Gestión regional o multisitio de instalaciones | required | 90% | +0.010 | 0.710 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-96027-20 | Documentación y trazabilidad de análisis | important | 90% | -0.020 | 0.290 | 100% | keyword_saturation_gte_80pct, low_hybrid_variance, hybrid_label_gap_below_0.03 |
| talentclef-75767-20 | Gestión de riesgos, calidad y entrega de sistemas mecánicos | important | 90% | -0.072 | 0.370 | 90% | keyword_saturation_gte_80pct |
| talentclef-90596-20 | Programas de mantenimiento preventivo | required | 90% | +0.094 | 0.860 | 95% | keyword_saturation_gte_80pct |
| talentclef-87280-20 | Gestión de residuos y limpieza de baños | important | 90% | +0.098 | 0.920 | 90% | keyword_saturation_gte_80pct |
| talentclef-85803-20 | Apoyo a originación y suscripción de préstamos | important | 90% | +0.109 | 1.000 | 90% | keyword_saturation_gte_80pct |
| talentclef-85803-20 | Preparación y revisión de documentación de préstamo | required | 90% | +0.120 | 0.910 | 95% | keyword_saturation_gte_80pct |
| talentclef-76474-20 | Operación de caja o sistema de punto de venta | required | 85% | +0.012 | 0.670 | 85% | keyword_saturation_gte_80pct, hybrid_label_gap_below_0.03 |
| talentclef-91821-20 | Desarrollo y mantenimiento de glosarios de datos | important | 85% | -0.042 | 0.360 | 90% | keyword_saturation_gte_80pct |
| talentclef-96027-20 | Ingeniería de sostenimiento y revisiones de diseño | important | 85% | +0.050 | 0.440 | 95% | keyword_saturation_gte_80pct |
| talentclef-96027-20 | Diseño y ejecución de planes de prueba | required | 85% | +0.051 | 0.820 | 95% | keyword_saturation_gte_80pct |
| talentclef-88540-20 | Colaboración con Customer Success durante el ciclo del cliente | important | 85% | +0.092 | 0.830 | 95% | keyword_saturation_gte_80pct |
| talentclef-87280-20 | Limpieza de suelos, superficies y mobiliario | required | 85% | +0.095 | 0.840 | 85% | keyword_saturation_gte_80pct |
| talentclef-76474-20 | Atención y servicio al cliente | required | 85% | +0.113 | 0.870 | 95% | keyword_saturation_gte_80pct |
| talentclef-88540-20 | Gestión de objetivos de ingresos y previsión de ventas | required | 85% | +0.124 | 0.880 | 85% | keyword_saturation_gte_80pct |
| talentclef-96356-20 | Análisis de datos en el dominio de salud | required | 85% | +0.271 | 1.000 | 85% | keyword_saturation_gte_80pct |
| talentclef-75767-20 | Liderazgo y coordinación multidisciplinar de proyectos | important | 80% | -0.024 | 0.320 | 100% | keyword_saturation_gte_80pct, hybrid_label_gap_below_0.03 |
| talentclef-91821-20 | Coordinación de flujos de gobernanza entre legal, seguridad y negocio | important | 80% | +0.026 | 0.620 | 100% | keyword_saturation_gte_80pct, hybrid_label_gap_below_0.03 |
| talentclef-85803-20 | Comunicación con prestatarios y profesionales inmobiliarios | important | 80% | +0.077 | 0.950 | 100% | keyword_saturation_gte_80pct |
| talentclef-88540-20 | Definición y ejecución de estrategia de ventas | required | 80% | +0.143 | 0.910 | 95% | keyword_saturation_gte_80pct |
| talentclef-96356-20 | Business Intelligence, tableros y visualización de datos | required | 80% | +0.157 | 0.880 | 80% | keyword_saturation_gte_80pct |
| talentclef-91821-20 | Seguridad de información y evaluación de riesgos | important | 80% | -0.179 | 0.140 | 80% | keyword_saturation_gte_80pct |
| talentclef-86302-20 | Certificación o cualificación docente relevante | preferred | 80% | +0.201 | 1.000 | 80% | keyword_saturation_gte_80pct |
| talentclef-96356-20 | Análisis estadístico aplicado | required | 80% | +0.209 | 0.910 | 85% | keyword_saturation_gte_80pct |
| talentclef-90596-20 | Gestión de activos, BMS y ciclo de vida de equipos | important | 70% | +0.008 | 0.590 | 100% | hybrid_label_gap_below_0.03 |
| talentclef-75767-20 | Titulación superior o licencia profesional en ingeniería mecánica | preferred | 70% | -0.011 | 0.470 | 100% | hybrid_label_gap_below_0.03, hybrid_auc_near_random |
| talentclef-75767-20 | Ingeniería mecánica aplicada a servicios de edificación | required | 65% | +0.020 | 0.520 | 95% | hybrid_label_gap_below_0.03, hybrid_auc_near_random |
| talentclef-86302-20 | Evaluación educativa y retroalimentación al alumnado | important | 55% | -0.001 | 0.448 | 65% | hybrid_label_gap_below_0.03 |
| talentclef-90596-20 | Instalaciones de vivienda multifamiliar o plomería | important | 50% | -0.025 | 0.450 | 75% | hybrid_label_gap_below_0.03, hybrid_auc_near_random |

## Comparación kw2.5 − kw1.0 con mayor aumento de saturación

| Caso | Criterio | Δ saturación | Δ gap híbrido | Δ AUC híbrida |
|---|---|---:|---:|---:|
| talentclef-91821-20 | Documentación para auditorías, incidentes y gestión de registros | +100% | -0.045 | +0.000 |
| talentclef-86302-20 | Gestión del aula y estrategias pedagógicas | +95% | +0.047 | +0.042 |
| talentclef-87280-20 | Gestión de residuos y limpieza de baños | +90% | -0.013 | +0.000 |
| talentclef-91821-20 | Asistencia legal o apoyo a un departamento jurídico | +90% | -0.015 | +0.070 |
| talentclef-88540-20 | Gestión de objetivos de ingresos y previsión de ventas | +85% | -0.100 | -0.070 |
| talentclef-90596-20 | Gestión regional o multisitio de instalaciones | +85% | +0.008 | +0.170 |
| talentclef-91821-20 | Desarrollo y mantenimiento de glosarios de datos | +85% | +0.025 | +0.060 |
| talentclef-86302-20 | Certificación o cualificación docente relevante | +80% | +0.083 | +0.000 |
| talentclef-87280-20 | Limpieza de suelos, superficies y mobiliario | +80% | -0.033 | -0.060 |
| talentclef-96356-20 | Business Intelligence, tableros y visualización de datos | +80% | -0.020 | -0.010 |
| talentclef-96356-20 | Análisis de datos en el dominio de salud | +80% | +0.025 | +0.000 |
| talentclef-75767-20 | Cumplimiento de códigos, normas y requisitos de proyecto | +75% | +0.012 | -0.180 |
| talentclef-75767-20 | Liderazgo y coordinación multidisciplinar de proyectos | +75% | +0.004 | -0.030 |
| talentclef-75767-20 | Diseño y optimización de sistemas HVAC | +75% | -0.106 | -0.050 |
| talentclef-75767-20 | Gestión de riesgos, calidad y entrega de sistemas mecánicos | +75% | -0.050 | -0.170 |
| talentclef-76474-20 | Manejo de efectivo y pagos con tarjeta | +75% | +0.044 | +0.020 |
| talentclef-90596-20 | Eficiencia energética y sistemas de gestión ambiental | +75% | +0.007 | +0.080 |
| talentclef-96027-20 | Diseño y ejecución de planes de prueba | +75% | -0.035 | +0.080 |
| talentclef-85803-20 | Apoyo a originación y suscripción de préstamos | +70% | -0.125 | +0.000 |
| talentclef-87280-20 | Limpieza, desinfección y estándares de higiene | +70% | -0.119 | +0.000 |
| talentclef-88540-20 | Definición y ejecución de estrategia de ventas | +70% | -0.044 | +0.000 |
| talentclef-91821-20 | Coordinación de flujos de gobernanza entre legal, seguridad y negocio | +70% | +0.001 | +0.040 |
| talentclef-91821-20 | Programas de privacidad y protección de datos | +70% | +0.075 | -0.070 |
| talentclef-91821-20 | Gobernanza y ciclo de vida de la información | +70% | -0.050 | -0.060 |
| talentclef-86302-20 | Experiencia con TOEFL u otros exámenes de inglés | +65% | -0.065 | +0.073 |

## Reproducción

```powershell
py -3 -m benchmark.audit.criteria_audit benchmark/results/manual_suites/talentclef-20-v1 --output benchmark/audit/reports/talentclef-20-v1
```
