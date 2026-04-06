# Workflow: Fase 4 — Entrenamiento Propio (Fine-tuning)

## PRERREQUISITO
- Fase 1, 2 y 3 completas
- Mínimo 500 análisis guardados en Supabase con retroalimentación del reclutador
- Lee CLAUDE.md antes de empezar

## Contexto
Fine-tuning del modelo sentence-transformers con datos propios de Malaquías.
El modelo aprende el vocabulario específico de reclutamiento en español.

## Tarea 1 — Pipeline de etiquetado en el frontend
En Results.jsx, añadir botones de feedback por candidato:
- 👍 "Buen match" — el reclutador confirma que este candidato era relevante
- 👎 "Mal match" — el candidato no era adecuado aunque el score era alto

Guardar en Supabase tabla nueva `feedback`:
```sql
CREATE TABLE feedback (
  id SERIAL PRIMARY KEY,
  candidato_id INTEGER REFERENCES candidatos(id),
  oferta_id INTEGER REFERENCES ofertas(id),
  user_id INTEGER REFERENCES users(id),
  label INTEGER,  -- 1 = buen match, 0 = mal match
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Tarea 2 — Endpoint de feedback en main.py
```python
@app.post("/feedback")
def save_feedback(
    candidato_id: int,
    label: int,  # 1 o 0
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # guardar en tabla feedback
```

## Tarea 3 — Script de exportación para fine-tuning
Crear `benchmark/export_training_data.py`:

```python
# Exporta pares (cv_text, job_description, label) desde Supabase
# Formato para sentence-transformers InputExample:
# InputExample(texts=[cv_text, job_description], label=1.0 o 0.0)
```

## Tarea 4 — Script de fine-tuning
Crear `benchmark/finetune_model.py`:

```python
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Cargar datos exportados
train_examples = [...]  # lista de InputExample

train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.CosineSimilarityLoss(model)

model.fit(
    train_objectives=[(train_dataloader, train_loss)],
    epochs=3,
    warmup_steps=100,
    output_path='models/malaquias-scorer-v1'
)
```

## Tarea 5 — Cargar modelo fine-tuned en matcher.py
```python
import os
MODEL_PATH = os.getenv("MODEL_PATH", "paraphrase-multilingual-MiniLM-L12-v2")
model = SentenceTransformer(MODEL_PATH)
```

Añadir variable de entorno `MODEL_PATH` al .env cuando el modelo esté listo.

## Notas importantes
- El fine-tuning requiere GPU para ser práctico — usar la branch GPU local (RTX 3070 Ti)
- Con CPU tarda horas para 500 ejemplos
- El modelo resultante se guarda localmente y se sube al VPS manualmente
- No ejecutar en producción hasta validar con el benchmark de Fase 2
