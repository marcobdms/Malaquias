# Adjudicación sin contaminar el gold

Esta carpeta guarda revisiones como capas separadas. El dato fuente no se modifica.

- `original`: etiquetas publicadas por el dataset.
- `provisional_adjudicated`: aplica hipótesis todavía no confirmadas.
- `unknown_aware`: excluye del cálculo las hipótesis provisionales.

Una opinión de IA nunca debe cambiar a `confirmed`. Esa transición requiere una
decisión humana documentada.
