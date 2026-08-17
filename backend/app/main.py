import os
from .config import load_environment

load_environment()

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
from .matcher import score_cvs_to_criteria, score_cvs_to_job
from .scoring_core import rank_candidate_results
from .llm import analyze_with_llm
from .utils import clean_text, truncate_text, validate_pdf_text
from .database import get_db, engine
from . import models
from .auth import hash_password, verify_password, create_access_token, get_current_user
from .job_criteria import build_job_descriptions, build_scoring_criteria, parse_job_criteria

class SaveAnalysisSchema(BaseModel):
    descripcion: str
    categoria: Optional[str] = None
    stack: Optional[str] = None
    balance: Optional[float] = 0.5
    candidatos: List[dict]
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MalaquÃ­as CV Screener")
MAX_CVS_PER_ANALYSIS = 20

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
        confirmed=True  # ConfirmaciÃ³n automÃ¡tica
    )
    db.add(user)
    db.commit()

    return {"message": "Cuenta creada exitosamente. Ya puedes iniciar sesiÃ³n."}


@app.get("/confirm")
def confirm_email(token: str, db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    from .auth import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        tipo = payload.get("type")
        if tipo != "confirm":
            raise HTTPException(status_code=400, detail="Token invÃ¡lido")
    except JWTError:
        raise HTTPException(status_code=400, detail="Token expirado o invÃ¡lido")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.confirmed = True
    db.commit()
    return {"message": "Cuenta confirmada. Ya puedes iniciar sesiÃ³n."}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

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
    criteria_json: Optional[str] = Form(None),
    cvs: List[UploadFile] = File(...),
    balance: float = Form(0.5),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    total = min(len(cvs), MAX_CVS_PER_ANALYSIS)
    try:
        criteria = parse_job_criteria(criteria_json)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    matching_job_description, explanation_job_description = build_job_descriptions(
        job_description, criteria
    )
    scoring_criteria = build_scoring_criteria(criteria)

    async def event_stream():
        yield f"data: {json.dumps({'event': 'start', 'total': total})}\n\n"

        parsed_candidates = []

        for i, cv in enumerate(cvs[:MAX_CVS_PER_ANALYSIS]):
            raw_text = extract_text_from_pdf(cv.file)
            candidate_id = f"cv-{i}"

            if not validate_pdf_text(raw_text):
                result = {
                    "candidate_id": candidate_id,
                    "filename": cv.filename,
                    "match_score": 0,
                    "ranking_score": 0,
                    "eligibility_state": "extraction_failed",
                    "analysis_status": "done",
                    "analysis": {"error": "PDF sin texto extraible"}
                }
                parsed_candidates.append({"result": result, "clean": ""})
            else:
                clean = clean_text(raw_text)
                result = {
                    "candidate_id": candidate_id,
                    "filename": cv.filename,
                    "match_score": 0,
                    "ranking_score": 0,
                    "eligibility_state": "pending",
                    "analysis_status": "pending",
                    "analysis": {"pending": True}
                }
                parsed_candidates.append({"result": result, "clean": clean})

        valid_indexes = [index for index, item in enumerate(parsed_candidates) if item["clean"]]
        valid_texts = [parsed_candidates[index]["clean"] for index in valid_indexes]
        if scoring_criteria:
            score_rows = score_cvs_to_criteria(
                valid_texts,
                scoring_criteria,
                strictness=strictness or "normal",
                balance=balance,
            )
        else:
            score_rows = score_cvs_to_job(
                valid_texts,
                matching_job_description,
                strictness=strictness or "normal",
                balance=balance,
            )

        for index, score_row in zip(valid_indexes, score_rows):
            result = parsed_candidates[index]["result"]
            result["match_score"] = round(score_row["display_score"] * 100, 2)
            result["ranking_score"] = score_row["ranking_score"]
            result["eligibility_state"] = score_row["eligibility_state"]
            result["required_coverage"] = score_row["required_coverage"]
            result["score_components"] = {
                "semantic_score": score_row["semantic_score"],
                "keyword_score": score_row["keyword_score"],
                "criteria": score_row["criteria_scores"],
            }

        results = rank_candidate_results(item["result"] for item in parsed_candidates)

        for result in results:
            yield f"data: {json.dumps({'event': 'cv_scored', 'total': total, 'result': result})}\n\n"

        llm_semaphore = asyncio.Semaphore(3)

        async def enrich_candidate(item):
            result = item["result"]
            if not item["clean"]:
                return result
            async with llm_semaphore:
                analysis = await asyncio.to_thread(
                    analyze_with_llm,
                    truncate_text(item["clean"]),
                    explanation_job_description,
                    categoria or "",
                    stack or "",
                    strictness or "normal",
                    result["match_score"] / 100,
                )
                result["analysis"] = analysis
                result["analysis_status"] = "error" if analysis.get("error") else "done"
                return result

        pending_items = [item for item in parsed_candidates if item["clean"]]
        done = len(results) - len(pending_items)
        for task in asyncio.as_completed([enrich_candidate(item) for item in pending_items]):
            result = await task
            done += 1
            yield f"data: {json.dumps({'event': 'llm_done', 'index': done, 'total': total, 'result': result})}\n\n"

        results = rank_candidate_results(results)
        yield f"data: {json.dumps({'event': 'complete', 'candidates': results})}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/save-analysis/")
def save_analysis(data: SaveAnalysisSchema, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Guarda un anÃ¡lisis explÃ­citamente."""
    oferta = models.Oferta(
        user_id=current_user.id,
        descripcion=data.descripcion,
        categoria=data.categoria,
        stack=data.stack
    )
    db.add(oferta)
    db.commit()
    db.refresh(oferta)

    for c in data.candidatos:
        analysis = c.get("analysis", {})
        candidato = models.Candidato(
            oferta_id=oferta.id,
            filename=c.get("filename"),
            match_score=c.get("match_score", 0),
            fortalezas=json.dumps(analysis.get("fortalezas", [])),
            carencias=json.dumps(analysis.get("carencias", [])),
            valoracion=analysis.get("valoracion", ""),
            recomendacion=analysis.get("recomendacion", ""),
            nombre_candidato=analysis.get("nombre_candidato"),
            titulo_candidato=analysis.get("titulo_candidato"),
            email_candidato=analysis.get("email_candidato"),
            telefono_candidato=analysis.get("telefono_candidato")
        )
        db.add(candidato)
    
    db.commit()
    return {"status": "ok", "oferta_id": oferta.id}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Sprint 2: Dashboard & Posiciones
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

from sqlalchemy import func

@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """MÃ©tricas del dashboard del usuario."""
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

    # DistribuciÃ³n de recomendaciones
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

    # Ãšltimos 5 candidatos
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
    """Obtiene los candidatos de una oferta especÃ­fica del usuario."""
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
            "nombre_candidato": c.nombre_candidato,
            "titulo_candidato": c.titulo_candidato,
            "created_at": c.created_at.isoformat() if c.created_at else None
        } for c in candidatos]
    }


@app.get("/ofertas/{oferta_id}/pdf")
def get_oferta_pdf(oferta_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    from fastapi.responses import Response
    from .report_pdf import generate_oferta_pdf
    
    oferta = db.query(models.Oferta).filter(
        models.Oferta.id == oferta_id,
        models.Oferta.user_id == current_user.id
    ).first()

    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    candidatos = db.query(models.Candidato).filter(
        models.Candidato.oferta_id == oferta_id
    ).all()

    pdf_buffer = generate_oferta_pdf(oferta, candidatos)
    return Response(content=pdf_buffer.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Reporte_Malaquias_Oferta_{oferta.id}.pdf"})

@app.delete("/ofertas/{oferta_id}")
def delete_oferta(oferta_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Elimina una oferta (posiciÃ³n) y todos sus candidatos."""
    oferta = db.query(models.Oferta).filter(
        models.Oferta.id == oferta_id,
        models.Oferta.user_id == current_user.id
    ).first()

    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    # Borrar candidatos en cascada manualmente para asegurar
    db.query(models.Candidato).filter(models.Candidato.oferta_id == oferta_id).delete()
    db.delete(oferta)
    db.commit()
    return {"message": "PosiciÃ³n y todos sus candidatos eliminados"}


@app.get("/talent-pool")
def talent_pool(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Devuelve todo el pool de talentos (candidatos) de todas las ofertas del usuario."""
    # Obtenemos los IDs de las ofertas del usuario
    user_ofertas = db.query(models.Oferta.id, models.Oferta.descripcion, models.Oferta.categoria).filter(
        models.Oferta.user_id == current_user.id
    ).all()
    
    if not user_ofertas:
        return []

    oferta_map = {o.id: {"descripcion": o.descripcion, "categoria": o.categoria} for o in user_ofertas}
    oferta_ids = list(oferta_map.keys())

    # Obtenemos todos los candidatos de esas ofertas
    candidatos = db.query(models.Candidato).filter(
        models.Candidato.oferta_id.in_(oferta_ids)
    ).order_by(models.Candidato.created_at.desc()).all()

    result = []
    for c in candidatos:
        result.append({
            "id": c.id,
            "filename": c.filename,
            "match_score": c.match_score,
            "recomendacion": c.recomendacion,
            "email_candidato": c.email_candidato,
            "telefono_candidato": c.telefono_candidato,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "oferta_id": c.oferta_id,
            "oferta_categoria": oferta_map[c.oferta_id]["categoria"],
            "oferta_descripcion": oferta_map[c.oferta_id]["descripcion"],
            "fortalezas": json.loads(c.fortalezas) if c.fortalezas else [],
            "carencias": json.loads(c.carencias) if c.carencias else [],
            "nombre_candidato": c.nombre_candidato,
            "titulo_candidato": c.titulo_candidato
        })

    return result

class ProfileUpdateRequest(BaseModel):
    nombre: str
    current_password: Optional[str] = None
    new_password: Optional[str] = None

@app.put("/profile")
def update_profile(data: ProfileUpdateRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Actualiza la informaciÃ³n del perfil del usuario."""
    # Si se envÃ­a nueva contraseÃ±a, validar y actualizar
    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="ContraseÃ±a actual incorrecta")
        current_user.password_hash = hash_password(data.new_password)
        
    current_user.nombre = data.nombre
    db.commit()
    
    return {"message": "Perfil actualizado", "nombre": current_user.nombre}

@app.delete("/reset-data")
def reset_data(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Borra todos los datos de anÃ¡lisis (ofertas y candidatos) del usuario actual."""
    ofertas = db.query(models.Oferta).filter(models.Oferta.user_id == current_user.id).all()
    oferta_ids = [o.id for o in ofertas]
    
    if oferta_ids:
        db.query(models.Candidato).filter(models.Candidato.oferta_id.in_(oferta_ids)).delete(synchronize_session=False)
        db.query(models.Oferta).filter(models.Oferta.user_id == current_user.id).delete(synchronize_session=False)
    
    db.commit()
    return {"message": "Todos tus datos han sido eliminados correctamente"}

@app.get("/health")
def health():
    return {"status": "ok"}
