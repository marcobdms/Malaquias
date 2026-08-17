"""Ejecuta un caso manual de 20 CV contra la API local de Malaquias."""

from __future__ import annotations

import argparse
import atexit
import json
import sys
import uuid
from contextlib import ExitStack
from pathlib import Path
from time import perf_counter
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmark.case_contract import load_case_request, request_form_data  # noqa: E402
from benchmark.metrics import evaluate_ranking  # noqa: E402
from benchmark.provenance import sha256_file  # noqa: E402
from backend.app.database import DATABASE_URL, SessionLocal  # noqa: E402
from backend.app.llm import get_provider  # noqa: E402
from backend.app.models import User  # noqa: E402


def _parse_sse(response: requests.Response) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data:"):
            continue
        events.append(json.loads(raw_line[5:].strip()))
    return events


def _authenticate(session: requests.Session, base_url: str) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:12]
    email = f"benchmark-{suffix}@malaquias.local"
    password = f"Benchmark-{suffix}!"
    register = session.post(
        f"{base_url}/register",
        json={"email": email, "password": password, "nombre": "Benchmark local"},
        timeout=30,
    )
    register.raise_for_status()
    login = session.post(
        f"{base_url}/login",
        data={"username": email, "password": password},
        timeout=30,
    )
    login.raise_for_status()
    return login.json()["access_token"], email


def _cleanup_benchmark_user(email: str) -> None:
    database = SessionLocal()
    try:
        database.query(User).filter(User.email == email).delete(synchronize_session=False)
        database.commit()
    finally:
        database.close()


def run_case(case_dir: Path, base_url: str) -> Path:
    if not DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("El runner manual solo admite una base SQLite local")

    case_dir = case_dir.resolve()
    truth = json.loads((case_dir / "ground_truth.json").read_text(encoding="utf-8"))
    case_request = load_case_request(case_dir, truth)
    expected = {row["filename"]: row for row in truth["candidates"]}

    session = requests.Session()
    token, benchmark_email = _authenticate(session, base_url)
    atexit.register(_cleanup_benchmark_user, benchmark_email)
    headers = {"Authorization": f"Bearer {token}"}

    request_started = perf_counter()
    with ExitStack() as stack:
        files = []
        for row in truth["candidates"]:
            path = case_dir / "cvs" / row["filename"]
            handle = stack.enter_context(path.open("rb"))
            files.append(("cvs", (path.name, handle, "application/pdf")))
        response = session.post(
            f"{base_url}/analyze",
            headers=headers,
            data=request_form_data(case_request),
            files=files,
            stream=True,
            timeout=(30, 1800),
        )
        response.raise_for_status()
        events = _parse_sse(response)
    total_seconds = perf_counter() - request_started

    complete = next((event for event in reversed(events) if event.get("event") == "complete"), None)
    if complete is None:
        raise RuntimeError("La API no emitio el evento complete")

    candidates = complete["candidates"]
    ranking = [row["filename"] for row in candidates]
    relevance = {
        filename: metadata["expected_relevance"] for filename, metadata in expected.items()
    }
    metrics = evaluate_ranking(ranking, relevance, cutoffs=(5, 10, 20))

    rows = []
    llm_errors = 0
    for position, candidate in enumerate(candidates, start=1):
        metadata = expected[candidate["filename"]]
        analysis = candidate.get("analysis") or {}
        if analysis.get("error"):
            llm_errors += 1
        rows.append(
            {
                "position": position,
                "filename": candidate["filename"],
                "candidate_id": metadata["candidate_id"],
                "expected_relevance": metadata["expected_relevance"],
                "match_score": candidate["match_score"],
                "ranking_score": candidate.get("ranking_score"),
                "eligibility_state": candidate.get("eligibility_state"),
                "required_coverage": candidate.get("required_coverage"),
                "score_components": candidate.get("score_components"),
                "analysis_status": candidate.get("analysis_status"),
                "recommendation": analysis.get("recomendacion"),
                "llm_error": analysis.get("error"),
                "analysis": analysis,
            }
        )

    true_positive = sum(
        row["expected_relevance"] == 1 and row["recommendation"] != "Descartar"
        for row in rows
    )
    false_negative = sum(
        row["expected_relevance"] == 1 and row["recommendation"] == "Descartar"
        for row in rows
    )
    false_positive = sum(
        row["expected_relevance"] == 0 and row["recommendation"] != "Descartar"
        for row in rows
    )
    true_negative = sum(
        row["expected_relevance"] == 0 and row["recommendation"] == "Descartar"
        for row in rows
    )
    predicted_positive = true_positive + false_positive
    actual_positive = true_positive + false_negative
    llm_classification = {
        "true_positive": true_positive,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "precision": true_positive / predicted_positive if predicted_positive else 0.0,
        "recall": true_positive / actual_positive if actual_positive else 0.0,
        "accuracy": (true_positive + true_negative) / len(rows) if rows else 0.0,
    }

    provider = get_provider()
    request_path = case_dir / "request.json"
    output = {
        "schema_version": "2.0",
        "case_id": truth["case_id"],
        "task": "api_pdf_full",
        "api_url": base_url,
        "llm_provider": provider.name,
        "llm_model": provider.model,
        "inputs": {
            "request": str(request_path) if request_path.exists() else "legacy offer.txt + criteria.json",
            "request_hash": sha256_file(request_path) if request_path.exists() else None,
            "ground_truth_hash": sha256_file(case_dir / "ground_truth.json"),
            "categoria": case_request["categoria"],
            "stack": case_request["stack"],
            "strictness": case_request["strictness"],
            "balance": case_request["balance"],
            "criteria_count": len(case_request["criteria"]),
        },
        "timing": {"total_seconds": round(total_seconds, 4)},
        "candidate_count": len(rows),
        "llm_error_count": llm_errors,
        "llm_classification": llm_classification,
        "metrics": metrics,
        "ranking": rows,
    }
    output_path = case_dir / "engine_result.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _cleanup_benchmark_user(benchmark_email)
    atexit.unregister(_cleanup_benchmark_user)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    output_path = run_case(args.case_dir, args.base_url.rstrip("/"))
    result = json.loads(output_path.read_text(encoding="utf-8"))
    print(json.dumps({
        "result": str(output_path),
        "candidate_count": result["candidate_count"],
        "llm_error_count": result["llm_error_count"],
        "metrics": result["metrics"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
