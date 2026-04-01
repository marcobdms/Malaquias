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

                result = {
                    "filename": cv.filename,
                    "match_score": round(score * 100, 2),
                    "analysis": analysis
                }

            results.append(result)
            yield f"data: {json.dumps({'event': 'cv_done', 'index': i + 1, 'total': total, 'result': result})}\n\n"
            await asyncio.sleep(0.05)

        results.sort(key=lambda x: x["match_score"], reverse=True)
        yield f"data: {json.dumps({'event': 'complete', 'candidates': results})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}