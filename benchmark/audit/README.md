# Auditoría de criterios

`criteria_audit.py` compara los runs emparejados `kw1.0` y `kw2.5` sin volver a
ejecutar el motor. Calcula por criterio saturación, media, varianza, separación
entre etiquetas, AUC pareada, tasa de confirmación y posiciones observadas.

```powershell
py -3 -m benchmark.audit.criteria_audit benchmark/results/manual_suites/talentclef-20-v1 --output benchmark/audit/reports/talentclef-20-v1
```

La etiqueta `non_discriminant` es una alerta reproducible. No reemplaza la
revisión humana, especialmente porque las etiquetas de TalentCLEF pueden tener
ruido y los runs actuales no persistieron fragmentos textuales de evidencia.
