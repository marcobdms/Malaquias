from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional
from sqlalchemy.orm import Session
import json
import asyncio

from .cv_parser import extract_text_from_pdf
from .matcher import compare_cv_to_job
from .llm import analyze_with_llm, detect_category
from .utils import clean_text, truncate_text, validate_pdf_text, is_valid_pdf
from .database import get_db, engine
from . import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Malaquías CV Screener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def route_engine(num_cvs: int, exhaustive: bool = False) -> dict:
    """Decide qué modo de análisis usar según el número de CVs."""
    if num_cvs <= 5:
        # Lote pequeño: el motor brilla con análisis completo para todos
        return {"mode": "exhaustive", "llm_top_n": num_cvs}
    elif num_cvs <= 20:
        # Lote mediano: hybrid — LLM para todos
        return {"mode": "hybrid", "llm_top_n": num_cvs}
    else:
        # Lote grande: solo keyword scoring, LLM para top 10
        return {"mode": "keyword_only", "llm_top_n": 10}


@app.post("/analyze")
async def analyze_cvs(
    job_description: str = Form(...),
    categoria: Optional[str] = Form(None),
    stack: Optional[str] = Form(None),
    strictness: Optional[str] = Form("normal"),
    cvs: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    total = min(len(cvs), 10)

    async def event_stream():
        yield f"data: {json.dumps({'event': 'start', 'total': total})}\n\n"

<<<<<<< Updated upstream
        oferta = models.Oferta(
            descripcion=job_description,
            categoria=categoria,
            stack=stack
        )
        db.add(oferta)
        db.commit()
        db.refresh(oferta)

=======
        # ── Fase 1: scoring matemático para todos (rápido, sin LLM) ──
        scored = []
        for cv in cvs[:total]:
            # --- Validaciones de Seguridad y Tipo ---
            if not is_valid_pdf(cv.content_type, cv.size or 0):
                scored.append({
                    "filename": cv.filename, 
                    "score": 0.0, 
                    "clean": "", 
                    "valid": False, 
                    "error": "Archivo inválido o excede 10MB"
                })
                continue
                
            try:
                raw_text = extract_text_from_pdf(cv.file)
                if not validate_pdf_text(raw_text):
                    scored.append({"filename": cv.filename, "score": 0.0, "clean": "", "valid": False, "error": "PDF sin texto extraíble"})
                else:
                    clean = clean_text(raw_text)
                    score = compare_cv_to_job(clean, job_description, strictness or "normal", balance=balance)
                    scored.append({"filename": cv.filename, "score": score, "clean": clean, "valid": True})
            except Exception as e:
                scored.append({"filename": cv.filename, "score": 0.0, "clean": "", "valid": False, "error": f"Error parseando PDF: {str(e)}"})

        # Ordenar por score antes de decidir cuántos reciben LLM
        scored.sort(key=lambda x: x["score"], reverse=True)

        # Auto-detect categoría si no viene en el form (una sola llamada Groq)
        effective_categoria = categoria or ""
        auto_keywords = []
        if not categoria:
            try:
                cat_result = detect_category(job_description)
                effective_categoria = cat_result.get("categoria", "")
                auto_keywords = cat_result.get("keywords_criticas", [])
                print(f"Auto-detect categoría: {effective_categoria}, keywords: {auto_keywords}")
            except Exception as e:
                print(f"Auto-detect falló (no crítico): {e}")

        engine_config = route_engine(total)
        llm_top_n = engine_config["llm_top_n"]
        print(f"Router: modo={engine_config['mode']}, llm_top_n={llm_top_n}, total={total}")

        # ── Fase 2: LLM solo para top N, stream de resultados ──
>>>>>>> Stashed changes
        results = []
        for i, cv_data in enumerate(scored):
            if not cv_data["valid"]:
                result = {
                    "filename": cv_data["filename"],
                    "match_score": 0,
                    "analysis": {"error": cv_data.get("error", "Error desconocido")}
                }
<<<<<<< Updated upstream
            else:
                clean = clean_text(raw_text)
                score = compare_cv_to_job(clean, job_description)
=======
            elif i < llm_top_n:
>>>>>>> Stashed changes
                analysis = analyze_with_llm(
                    truncate_text(cv_data["clean"]),
                    job_description,
                    effective_categoria,
                    stack or "",
<<<<<<< Updated upstream
                    strictness or "normal"
                )

                candidato = models.Candidato(
                    oferta_id=oferta.id,
                    filename=cv.filename,
                    match_score=round(score * 100, 2),
                    fortalezas=json.dumps(analysis.get("fortalezas", [])),
                    carencias=json.dumps(analysis.get("carencias", [])),
                    valoracion=analysis.get("valoracion", ""),
                    recomendacion=analysis.get("recomendacion", ""),
                    email_candidato=analysis.get("email_candidato"),
                    telefono_candidato=analysis.get("telefono_candidato")
                )
                db.add(candidato)
                db.commit()

=======
                    strictness or "normal",
                    match_score=cv_data["score"]
                )
>>>>>>> Stashed changes
                result = {
                    "filename": cv_data["filename"],
                    "match_score": round(cv_data["score"] * 100, 2),
                    "analysis": analysis
                }
                await asyncio.sleep(1.5)  # throttle solo cuando hay llamada LLM
            else:
                # Score matemático sin análisis LLM
                result = {
                    "filename": cv_data["filename"],
                    "match_score": round(cv_data["score"] * 100, 2),
                    "analysis": {"scored_only": True}
                }

            results.append(result)
            yield f"data: {json.dumps({'event': 'cv_done', 'index': i + 1, 'total': total, 'result': result})}\n\n"
<<<<<<< Updated upstream
            await asyncio.sleep(0.05)
=======
>>>>>>> Stashed changes

        yield f"data: {json.dumps({'event': 'complete', 'candidates': results})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}