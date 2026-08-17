import os
import hashlib
from datetime import datetime, timedelta
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models
from .config import load_environment
from .database import get_db

load_environment()

SECRET_KEY = os.getenv("SECRET_KEY", "cambia_esto_por_algo_seguro")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días

PASSWORD_HASH_PREFIX = "malaquias-bcrypt-sha256$"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def _password_digest(password: str) -> bytes:
    return hashlib.sha256(password.encode("utf-8")).digest()

def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(_password_digest(password), bcrypt.gensalt())
    return PASSWORD_HASH_PREFIX + hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False

    try:
        if hashed.startswith(PASSWORD_HASH_PREFIX):
            stored = hashed.removeprefix(PASSWORD_HASH_PREFIX).encode("utf-8")
            return bcrypt.checkpw(_password_digest(plain), stored)

        legacy_password = plain.encode("utf-8")
        if len(legacy_password) > 72:
            return False
        return bcrypt.checkpw(legacy_password, hashed.encode("utf-8"))
    except (TypeError, ValueError):
        return False

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
