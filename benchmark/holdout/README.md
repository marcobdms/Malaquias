# Pools candidatos ECYL × TalentCLEF

Este conjunto **no es todavía un gold set**. Congela nueve ofertas reales de
ECYL y veinte perfiles de TalentCLEF por oferta con estado
`incoming_unjudged`. No se calculan métricas y no debe usarse para calibrar.

La selección solo usa `baseline.json` sobre el texto bruto de cada oferta:

- 8 candidatos del top del baseline;
- 6 candidatos reproducibles de los puestos 9–60;
- 6 candidatos aleatorios reproducibles de la cola 61–472.

Así se mezclan encajes plausibles, casos cercanos y controles sin usar
criterios v2, `lexical_v2`, Gemini ni etiquetas de TalentCLEF. La selección no
afirma que un candidato sea positivo o negativo.

Los tres pools prioritarios para la primera revisión humana son ciberseguridad
IT, comercial/ventas y logística/carretilla. Los otros seis quedan congelados
para revisiones posteriores.

## Reconstrucción

Desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m benchmark.scripts.create_ecyl_holdout_pools
```

El manifiesto y los IDs congelados se guardan en `benchmark/manifests/` y
`benchmark/pools/`. Los 180 PDF se generan en `benchmark/results/`, ignorado por
Git. Cada PDF conserva el texto del perfil fuente; sirve para probar parser/UI,
pero el TXT y su SHA-256 son la referencia canónica.

Los metadatos usan exclusivamente el identificador anónimo del perfil. No
copian nombres ni otros campos de identidad desde el contenido fuente.

No ejecutar variantes experimentales sobre estos pools hasta completar y
sellar una adjudicación humana independiente.
