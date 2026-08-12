"""Carga segura de configuración local y de despliegue."""

from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_environment() -> None:
    """Prioriza .env.local sin impedir variables inyectadas por la plataforma."""

    load_dotenv(PROJECT_ROOT / ".env.local", override=False)
    load_dotenv(PROJECT_ROOT / ".env", override=False)
