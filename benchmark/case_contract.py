"""Contrato reproducible entre un caso manual, la UI y sus runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUEST_FIELDS = (
    "job_description",
    "categoria",
    "stack",
    "strictness",
    "balance",
    "criteria",
)


def build_case_request(
    job_description: str,
    criteria: list[dict[str, Any]],
    *,
    categoria: str = "",
    stack: str = "",
    strictness: str = "normal",
    balance: float = 0.5,
) -> dict[str, Any]:
    if not job_description.strip():
        raise ValueError("La oferta del caso no puede estar vacía")
    if strictness not in {"estricto", "normal", "flexible"}:
        raise ValueError("Strictness no soportado")
    if not 0.0 <= float(balance) <= 1.0:
        raise ValueError("Balance debe estar entre 0 y 1")
    return {
        "schema_version": "1.0",
        "job_description": job_description,
        "categoria": categoria,
        "stack": stack,
        "strictness": strictness,
        "balance": float(balance),
        "criteria": criteria,
    }


def load_case_request(
    case_dir: Path,
    truth: dict[str, Any],
    request_path: Path | None = None,
) -> dict[str, Any]:
    """Lee request.json; mantiene compatibilidad con casos anteriores."""

    selected_path = request_path.resolve() if request_path else case_dir / "request.json"
    if selected_path.exists():
        payload = json.loads(selected_path.read_text(encoding="utf-8"))
        missing = [field for field in REQUEST_FIELDS if field not in payload]
        if missing:
            raise ValueError(f"request.json no contiene: {', '.join(missing)}")
        return build_case_request(
            str(payload["job_description"]),
            list(payload["criteria"]),
            categoria=str(payload.get("categoria", "")),
            stack=str(payload.get("stack", "")),
            strictness=str(payload["strictness"]),
            balance=float(payload["balance"]),
        )
    if request_path is not None:
        raise FileNotFoundError(f"No existe el request solicitado: {selected_path}")

    offer = (case_dir / "offer.txt").read_text(encoding="utf-8")
    criteria = json.loads((case_dir / "criteria.json").read_text(encoding="utf-8"))
    return build_case_request(
        offer,
        criteria,
        categoria=str(truth.get("categoria", "")),
        stack=str(truth.get("stack", "")),
        strictness=str(truth.get("strictness", "normal")),
        balance=float(truth.get("balance", 0.5)),
    )


def request_form_data(request: dict[str, Any]) -> dict[str, str]:
    """Serializa exactamente los campos que App.jsx envía como FormData."""

    return {
        "job_description": str(request["job_description"]),
        "categoria": str(request.get("categoria", "")),
        "stack": str(request.get("stack", "")),
        "strictness": str(request["strictness"]),
        "balance": str(float(request["balance"])),
        "criteria_json": json.dumps(request["criteria"], ensure_ascii=False),
    }
