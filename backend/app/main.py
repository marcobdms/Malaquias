from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from sqlalchemy.orm import Session
import json

from .cv_parser import extract_text_from_pdf
from .matcher import compare_cv_to_job
from .llm import analyze_with_llm
from .utils import clean_text, truncate_text, validate_pdf_text
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


@app.post("/analyze")
async def analyze_cvs(
    job_description: str = Form(...),
    categoria: Optional[str] = Form(None),
    stack: Optional[str] = Form(None),
    cvs: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    oferta = models.Oferta(
        descripcion=job_description,
        categoria=categoria,
        stack=stack
    )
    db.add(oferta)
    db.commit()
    db.refresh(oferta)

    results = []

    for cv in cvs[:10]:
        raw_text = extract_text_from_pdf(cv.file)

        if not validate_pdf_text(raw_text):
            results.append({
                "filename": cv.filename,
                "match_score": 0,
                "analysis": {"error": "PDF sin texto extraíble"}
            })
            continue

        clean = clean_text(raw_text)
        score = compare_cv_to_job(clean, job_description)
        analysis = analyze_with_llm(truncate_text(clean), job_description, categoria or "", stack or "")

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

        results.append({
            "filename": cv.filename,
            "match_score": round(score * 100, 2),
            "analysis": analysis
        })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return {"candidates": results}


@app.get("/health")
def health():
    return {"status": "ok"}