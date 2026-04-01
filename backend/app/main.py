import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import json
import asyncio

from .cv_parser import extract_text_from_pdf
from .matcher import compare_cv_to_job
from .llm import analyze_with_llm
from .utils import clean_text, truncate_text, validate_pdf_text
from .database import get_db, engine
from . import models
from .auth import hash_password, verify_password, create_access_token, get_current_user
from .email_service import send_confirmation_email

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Malaquías CV Screener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RegisterRequest(BaseModel):
    email: str
    password: str
    nombre: str


@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")

    confirm_token = create_access_token({"sub": data.email, "type": "confirm"})

    user = models.User(
        email=data.email,
        nombre=data.nombre,
        password_hash=hash_password(data.password),
        confirmed=False
    )
    db.add(user)
    db.commit()

    send_confirmation_email(data.email, data.nombre, confirm_token)
    return {"message": "Cuenta creada. Revisa tu email para confirmarla."}


@app.get("/confirm")
def confirm_email(token: str, db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    from .auth import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        tipo = payload.get("type")
        if tipo != "confirm":
            raise HTTPException(status_code=400, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=400, detail="Token expirado o inválido")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.confirmed = True
    db.commit()
    return {"message": "Cuenta confirmada. Ya puedes iniciar sesión."}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not user.confirmed:
        raise HTTPException(status_code=403, detail="Confirma tu email antes de iniciar sesión")

    token = create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "nombre": user.nombre}


@app.get("/me")
def me(current_user=Depends(get_current_user)):
    return {"email": current_user.email, "nombre": current_user.nombre}


@app.post("/analyze")
async def analyze_cvs(
    job_description: str = Form(...),
    categoria: Optional[str] = Form(None),
    stack: Optional[str] = Form(None),
    strictness: Optional[str] = Form("normal"),
    cvs: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    total = min(len(cvs), 10)

    async def event_stream():
        yield f"data: {json.dumps({'event': 'start', 'total': total})}\n\n"

        oferta = models.Oferta(
            user_id=current_user.id,
            descripcion=job_description,
            categoria=categoria,
            stack=stack
        )
        db.add(oferta)
        db.commit()
        db.refresh(oferta)

        results = []

        for i, cv in enumerate(cvs[:10]):
            raw_text = extract_text_from_pdf(cv.file)

            if not validate_pdf_text(raw_text):
                result = {
                    "filename": cv.filename,
                    "match_score": 0,
                    "analysis": {"error": "PDF sin texto extraíble"}
                }
            else:
                clean = clean_text(raw_text)
                score = compare_cv_to_job(clean, job_description, strictness or "normal")
                analysis = analyze_with_llm(
                    truncate_text(clean),
                    job_description,
                    categoria or "",
                    stack or "",
                    strictness or "normal",
                    match_score=score
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

                result = {
                    "filename": cv.filename,
                    "match_score": round(score * 100, 2),
                    "analysis": analysis
                }

            results.append(result)
            yield f"data: {json.dumps({'event': 'cv_done', 'index': i + 1, 'total': total, 'result': result})}\n\n"
            await asyncio.sleep(1.5)

        results.sort(key=lambda x: x["match_score"], reverse=True)
        yield f"data: {json.dumps({'event': 'complete', 'candidates': results})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ──────────────────────────────────────
# Sprint 2: Dashboard & Posiciones
# ──────────────────────────────────────

from sqlalchemy import func

@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Métricas del dashboard del usuario."""
    user_ofertas = db.query(models.Oferta).filter(models.Oferta.user_id == current_user.id).all()
    oferta_ids = [o.id for o in user_ofertas]

    total_ofertas = len(user_ofertas)

    if not oferta_ids:
        return {
            "total_ofertas": 0,
            "total_candidatos": 0,
            "score_promedio": 0,
            "distribucion": {"entrevistar": 0, "considerar": 0, "descartar": 0},
            "ultimos_candidatos": []
        }

    total_candidatos = db.query(func.count(models.Candidato.id)).filter(
        models.Candidato.oferta_id.in_(oferta_ids)
    ).scalar()

    score_promedio = db.query(func.avg(models.Candidato.match_score)).filter(
        models.Candidato.oferta_id.in_(oferta_ids),
        models.Candidato.match_score > 0
    ).scalar() or 0

    # Distribución de recomendaciones
    all_candidatos = db.query(models.Candidato).filter(
        models.Candidato.oferta_id.in_(oferta_ids),
        models.Candidato.recomendacion != None,
        models.Candidato.recomendacion != ""
    ).all()

    dist = {"entrevistar": 0, "considerar": 0, "descartar": 0}
    for c in all_candidatos:
        rec = (c.recomendacion or "").lower()
        if "entrevistar" in rec:
            dist["entrevistar"] += 1
        elif "considerar" in rec:
            dist["considerar"] += 1
        elif "descartar" in rec:
            dist["descartar"] += 1

    # Últimos 5 candidatos
    ultimos = db.query(models.Candidato).filter(
        models.Candidato.oferta_id.in_(oferta_ids)
    ).order_by(models.Candidato.created_at.desc()).limit(5).all()

    ultimos_data = [{
        "id": c.id,
        "filename": c.filename,
        "match_score": c.match_score,
        "recomendacion": c.recomendacion,
        "oferta_id": c.oferta_id,
        "created_at": c.created_at.isoformat() if c.created_at else None
    } for c in ultimos]

    return {
        "total_ofertas": total_ofertas,
        "total_candidatos": total_candidatos,
        "score_promedio": round(float(score_promedio), 1),
        "distribucion": dist,
        "ultimos_candidatos": ultimos_data
    }


@app.get("/ofertas")
def list_ofertas(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Lista todas las ofertas/posiciones del usuario con conteo de candidatos."""
    ofertas = db.query(models.Oferta).filter(
        models.Oferta.user_id == current_user.id
    ).order_by(models.Oferta.created_at.desc()).all()

    result = []
    for o in ofertas:
        count = db.query(func.count(models.Candidato.id)).filter(
            models.Candidato.oferta_id == o.id
        ).scalar()

        result.append({
            "id": o.id,
            "descripcion": o.descripcion[:120] + "..." if len(o.descripcion) > 120 else o.descripcion,
            "categoria": o.categoria,
            "stack": o.stack,
            "total_candidatos": count,
            "created_at": o.created_at.isoformat() if o.created_at else None
        })

    return result


@app.get("/ofertas/{oferta_id}/candidatos")
def get_oferta_candidatos(oferta_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Obtiene los candidatos de una oferta específica del usuario."""
    oferta = db.query(models.Oferta).filter(
        models.Oferta.id == oferta_id,
        models.Oferta.user_id == current_user.id
    ).first()

    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    candidatos = db.query(models.Candidato).filter(
        models.Candidato.oferta_id == oferta_id
    ).order_by(models.Candidato.match_score.desc()).all()

    return {
        "oferta": {
            "id": oferta.id,
            "descripcion": oferta.descripcion,
            "categoria": oferta.categoria,
            "stack": oferta.stack,
            "created_at": oferta.created_at.isoformat() if oferta.created_at else None
        },
        "candidatos": [{
            "id": c.id,
            "filename": c.filename,
            "match_score": c.match_score,
            "fortalezas": json.loads(c.fortalezas) if c.fortalezas else [],
            "carencias": json.loads(c.carencias) if c.carencias else [],
            "valoracion": c.valoracion,
            "recomendacion": c.recomendacion,
            "email_candidato": c.email_candidato,
            "telefono_candidato": c.telefono_candidato,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in candidatos]
    }


@app.get("/health")
def health():
    return {"status": "ok"}