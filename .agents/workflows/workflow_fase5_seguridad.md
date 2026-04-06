# Workflow: Fase 5 — Seguridad y Escalabilidad

## PRERREQUISITO
Lee CLAUDE.md antes de empezar.
Este workflow añade capas de seguridad sin cambiar funcionalidad existente.

## Tarea 1 — Rate limiting con slowapi
Instalar: añadir `slowapi` a requirements.txt

En main.py:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, ...):

@app.post("/register")  
@limiter.limit("3/minute")
def register(request: Request, ...):
```

## Tarea 2 — Refresh tokens JWT
En auth.py añadir:
```python
REFRESH_TOKEN_EXPIRE_DAYS = 30
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # reducir de 7 días a 15 minutos

def create_refresh_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {**data, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

Nuevo endpoint /refresh:
```python
@app.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    # verificar refresh token, devolver nuevo access token
```

En frontend: interceptar 401 y llamar /refresh automáticamente antes de logout.

## Tarea 3 — Headers de seguridad
En main.py añadir middleware de headers:
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

## Tarea 4 — Limpieza automática disco VPS
Crear script backend/scripts/cleanup_docker.sh:
```bash
#!/bin/bash
# Ejecutar semanalmente con cron
docker system prune -f
journalctl --vacuum-size=200M
echo "Limpieza completada: $(date)"
```

Añadir al crontab del VPS:
```
0 3 * * 0 /bin/bash /path/to/cleanup_docker.sh >> /var/log/cleanup.log 2>&1
```

## Verificación
- /login debe devolver 429 después de 5 intentos en 1 minuto
- /register debe devolver 429 después de 3 intentos en 1 minuto
- Access token debe expirar en 15 minutos
- Refresh token debe funcionar silenciosamente en el frontend
