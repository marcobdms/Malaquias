# Laboratorio de Benchmark — Malaquías

Este directorio contiene la infraestructura para probar y evaluar la precisión del motor de scoring (`matcher.py`). 
El sistema evalúa CVs contra descripciones de trabajo base usando tres métricas típicas de Information Retrieval:

- **NDCG@3**: Mide la calidad del Top 3 valorando especialmente que los CVs de mayor relevancia aparezcan en las posiciones más altas.
- **Precision@3**: Porcentaje del Top 3 que son verdaderamente relevantes (relevancia >= 2).
- **MRR (Mean Reciprocal Rank)**: Posición del primer resultado perfecto (relevancia = 3). Cuanto más cerca del número 1, mejor.

## Estructura de Datos
El directorio `dataset/` contiene carpetas por categoría (it_sistemas, ventas, logistica, desarrollo). Cada una tiene:
- `oferta.txt`: Texto libre con la descripción del puesto.
- `cvs/`: Carpeta vacía por defecto. **Debes añadir los PDFs aquí** que quieras probar para esa categoría.

## `expected_rankings.json`
Este archivo mapea la verdad absoluta (Ground Truth). Para los CVs de prueba que coloques, define:
- `relevancia 3`: Exactamente lo que se busca (debería ser contratado).
- `relevancia 2`: Bueno, útil, transferible.
- `relevancia 1`: Relacionado pero bajo nivel.
- `relevancia 0`: No relacionado.

## Uso
Para procesar los CVs y medir el motor, ejecuta:
```bash
python benchmark/run_benchmark.py
```

El script imprimirá una tabla resumen en la consola y dejará un reporte detallado (JSON) en la carpeta `results/`.
