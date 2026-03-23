from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    ofertas = relationship("Oferta", back_populates="user")


class Oferta(Base):
    __tablename__ = "ofertas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    descripcion = Column(Text, nullable=False)
    categoria = Column(String)
    stack = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ofertas")
    candidatos = relationship("Candidato", back_populates="oferta")


class Candidato(Base):
    __tablename__ = "candidatos"

    id = Column(Integer, primary_key=True, index=True)
    oferta_id = Column(Integer, ForeignKey("ofertas.id"), nullable=False)
    filename = Column(String)
    match_score = Column(Float)
    fortalezas = Column(Text)
    carencias = Column(Text)
    valoracion = Column(Text)
    recomendacion = Column(String)
    email_candidato = Column(String)
    telefono_candidato = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    oferta = relationship("Oferta", back_populates="candidatos")