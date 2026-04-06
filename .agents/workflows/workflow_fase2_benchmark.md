# Workflow: Fase 2 — Laboratorio de Benchmark

## Contexto
Lee primero CLAUDE.md.
Este workflow crea la infraestructura de testing del motor de scoring.
No modifica código de la aplicación — solo crea scripts de medición.

## Estructura a crear
```
benchmark/
├── README.md
├── dataset/
│   ├── it_sistemas/
│   │   ├── oferta.txt
│   │   └── cvs/          (vacío, el usuario añade sus CVs)
│   ├── ventas/
│   │   ├── oferta.txt
│   │   └── cvs/
│   ├── logistica/
│   │   ├── oferta.txt
│   │   └── cvs/
│   └── desarrollo/
│       ├── oferta.txt
│       └── cvs/
├── expected_rankings.json
├── run_benchmark.py
└── results/
    └── .gitkeep
```

## Tarea 1 — Crear ofertas de prueba

### dataset/it_sistemas/oferta.txt
```
Administrador de Sistemas IT
Buscamos administrador de sistemas responsable de servidores, redes y seguridad informática.
Requisitos: Windows Server, Linux, Active Directory, VPN, Firewall, VMware, soporte técnico usuarios.
Experiencia mínima 2-3 años en administración de sistemas y redes TCP/IP.
```

### dataset/ventas/oferta.txt
```
Commercial Sales Manager Internacional
Buscamos perfil comercial con experiencia en ventas B2B internacionales.
Requisitos: CRM, Salesforce, inglés C1, negociación, gestión de cartera de clientes.
Experiencia mínima 3 años en ventas y desarrollo de negocio.
```

### dataset/logistica/oferta.txt
```
Mozo de Almacén con Carnet de Montacargas
Buscamos mozo de almacén para centro logístico en Madrid.
Requisitos: carnet montacargas, manejo PDA, picking, packing, preparación de pedidos.
Experiencia en almacén y gestión de inventario.
```

### dataset/desarrollo/oferta.txt
```
Backend Developer Python
Buscamos desarrollador backend con experiencia en Python y APIs REST.
Requisitos: Python, FastAPI o Django, SQL, PostgreSQL, Docker, Git.
Experiencia mínima 2 años en desarrollo backend.
```

## Tarea 2 — Crear expected_rankings.json
```json
{
  "it_sistemas": {
    "oferta": "dataset/it_sistemas/oferta.txt",
    "descripcion": "Administrador de Sistemas IT",
    "ranking_esperado": [
      {"cv": "cv_sysadmin_senior.pdf", "relevancia": 3, "motivo": "Experiencia directa Windows/Linux/AD"},
      {"cv": "cv_helpdesk_junior.pdf", "relevancia": 2, "motivo": "Soporte técnico, transferible"},
      {"cv": "cv_developer_python.pdf", "relevancia": 1, "motivo": "Técnico pero diferente stack"},
      {"cv": "cv_camara.pdf", "relevancia": 0, "motivo": "Sin relación"},
      {"cv": "cv_psicologia.pdf", "relevancia": 0, "motivo": "Sin relación"}
    ]
  },
  "ventas": {
    "oferta": "dataset/ventas/oferta.txt",
    "descripcion": "Sales Manager Internacional",
    "ranking_esperado": [
      {"cv": "cv_account_manager.pdf", "relevancia": 3, "motivo": "Ventas B2B directas"},
      {"cv": "cv_rrhh_ingles.pdf", "relevancia": 1, "motivo": "Habilidades blandas, sin ventas"},
      {"cv": "cv_tecnico_it.pdf", "relevancia": 0, "motivo": "Sin relación comercial"}
    ]
  },
  "logistica": {
    "oferta": "dataset/logistica/oferta.txt",
    "descripcion": "Mozo Almacén con Montacargas",
    "ranking_esperado": [
      {"cv": "cv_mozo_montacargas.pdf", "relevancia": 3, "motivo": "Certificado + experiencia directa"},
      {"cv": "cv_mozo_sin_certificado.pdf", "relevancia": 2, "motivo": "Experiencia pero sin certificado"},
      {"cv": "cv_amazon_operaciones.pdf", "relevancia": 1, "motivo": "Entorno logístico, diferente rol"},
      {"cv": "cv_camara.pdf", "relevancia": 0, "motivo": "Sin relación"}
    ]
  }
}
```

## Tarea 3 — Crear run_benchmark.py
Script que:
1. Lee cada categoría del expected_rankings.json
2. Para cada categoría, carga la oferta y los CVs de la carpeta correspondiente
3. Llama al matcher local (importa directamente matcher.py y keyword_matcher.py)
4. Compara el ranking obtenido vs el esperado
5. Calcula métricas:
   - **NDCG@3**: calidad del top 3
   - **Precision@3**: de los 3 primeros, cuántos tienen relevancia >= 2
   - **MRR**: posición del primer resultado con relevancia = 3
6. Guarda resultado en results/benchmark_{timestamp}.json
7. Imprime tabla comparativa en terminal

```python
# Estructura del script
import json
import sys
from pathlib import Path
from datetime import datetime

# Añadir backend al path
sys.path.append(str(Path(__file__).parent.parent / "backend"))
from app.matcher import compare_cv_to_job
from app.cv_parser import extract_text_from_pdf

def ndcg_at_k(ranking_obtenido, relevancias_esperadas, k=3):
    # implementar NDCG
    pass

def precision_at_k(ranking_obtenido, relevancias_esperadas, k=3, threshold=2):
    # implementar Precision@K
    pass

def run_benchmark(config_path, balance=0.5, strictness="normal"):
    # cargar config, correr motor, medir, guardar
    pass

if __name__ == "__main__":
    run_benchmark("expected_rankings.json")
```

## Tarea 4 — README del benchmark
Crea benchmark/README.md explicando:
- Cómo añadir CVs al dataset
- Cómo ejecutar el benchmark: `python run_benchmark.py`
- Cómo interpretar las métricas
- Cómo comparar versiones del motor

## Verificación
- `python run_benchmark.py` debe ejecutarse sin errores aunque no haya CVs en las carpetas
- Debe imprimir "No hay CVs en dataset/X, saltando" si la carpeta está vacía
- No debe modificar ningún archivo del backend o frontend
