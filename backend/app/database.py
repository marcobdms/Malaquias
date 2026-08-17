import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import PROJECT_ROOT, load_environment

load_environment()

def normalize_sqlite_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///") or database_url.startswith("sqlite:////"):
        return database_url

    sqlite_path = database_url.removeprefix("sqlite:///")
    if sqlite_path == ":memory:" or Path(sqlite_path).is_absolute():
        return database_url

    resolved_path = (PROJECT_ROOT / sqlite_path).resolve().as_posix()
    return f"sqlite:///{resolved_path}"


DATABASE_URL = normalize_sqlite_url(os.getenv("DATABASE_URL", "sqlite:///./backend/malaquias_local.db"))

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
