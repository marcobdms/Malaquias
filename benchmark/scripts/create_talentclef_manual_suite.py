"""Genera diez casos PDF reproducibles para validar el pipeline local de Malaquias."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.case_contract import build_case_request  # noqa: E402
from benchmark.provenance import sha256_file  # noqa: E402
from benchmark.scripts.create_manual_case import (  # noqa: E402
    SOURCE_URL,
    build_pdf,
    read_positive_ids,
)


DEFAULT_SOURCE = (
    REPO_ROOT
    / "benchmark/data/downloaded/talentclef_2026_task_a/extracted/TaskA/development/es"
)
DEFAULT_CATALOG = REPO_ROOT / "benchmark/criteria/talentclef-development-es-v1.json"
DEFAULT_HARD_POOL = REPO_ROOT / "benchmark/pools/talentclef-hard-negatives-es.json"
DEFAULT_OUTPUT = REPO_ROOT / "benchmark/results/manual_suites/talentclef-20-v1"
DEFAULT_SEED = 20260816
TARGET_POSITIVES = 10
TARGET_CANDIDATES = 20


def select_case_candidates(
    positive_ids: list[str],
    frozen_pool_ids: list[str],
    *,
    query_id: str,
    seed: int,
    target_positives: int = TARGET_POSITIVES,
    target_candidates: int = TARGET_CANDIDATES,
) -> tuple[list[str], list[str], int]:
    """Selecciona positivos unicos y completa con negativos del pool baseline."""

    unique_positives = sorted(set(str(value) for value in positive_ids))
    positive_set = set(unique_positives)
    positive_count = min(target_positives, len(unique_positives))
    rng = random.Random(seed + int(query_id))
    selected_positives = sorted(rng.sample(unique_positives, positive_count))
    needed_negatives = target_candidates - positive_count
    available_negatives = [
        str(value)
        for value in dict.fromkeys(frozen_pool_ids)
        if str(value) not in positive_set
    ]
    if len(available_negatives) < needed_negatives:
        raise ValueError(
            f"La query {query_id} solo tiene {len(available_negatives)} negativos "
            f"baseline; se necesitan {needed_negatives}"
        )
    selected_negatives = available_negatives[:needed_negatives]
    shortfall = target_positives - positive_count
    return selected_positives, selected_negatives, shortfall


def _load_jobs(catalog_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    jobs = payload.get("jobs", [])
    if len(jobs) != 10:
        raise ValueError("El catalogo de criterios debe contener exactamente 10 ofertas")
    return jobs


def _register_font() -> None:
    try:
        pdfmetrics.getFont("BenchmarkArial")
    except KeyError:
        pdfmetrics.registerFont(TTFont("BenchmarkArial", "C:/Windows/Fonts/arial.ttf"))


def _first_nonempty_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "Candidato")


def generate_suite(
    source: Path,
    catalog_path: Path,
    hard_pool_path: Path,
    output: Path,
    *,
    seed: int = DEFAULT_SEED,
) -> Path:
    source = source.resolve()
    catalog_path = catalog_path.resolve()
    hard_pool_path = hard_pool_path.resolve()
    output = output.resolve()
    hard_pool = json.loads(hard_pool_path.read_text(encoding="utf-8"))
    frozen_queries = hard_pool.get("queries", {})
    jobs = _load_jobs(catalog_path)
    _register_font()

    case_entries: list[dict[str, Any]] = []
    for job in jobs:
        query_id = str(job["query_id"])
        offer_path = source / "queries" / query_id
        offer = offer_path.read_text(encoding="utf-8")
        if sha256_file(offer_path) != job["job_text_sha256"]:
            raise ValueError(f"La oferta {query_id} no coincide con el catalogo de criterios")
        if query_id not in frozen_queries:
            raise ValueError(f"La query {query_id} no existe en el pool de negativos baseline")

        positive_ids = read_positive_ids(source / "qrels.tsv", query_id)
        positives, negatives, shortfall = select_case_candidates(
            positive_ids,
            list(frozen_queries[query_id]),
            query_id=query_id,
            seed=seed,
        )
        case_id = f"talentclef-{query_id}-20"
        case_dir = output / case_id
        cv_dir = case_dir / "cvs"
        cv_dir.mkdir(parents=True, exist_ok=True)

        selections = [(value, 1, "relevant") for value in positives]
        selections.extend((value, 0, "hard_negative") for value in negatives)
        records: list[dict[str, Any]] = []
        for index, (candidate_id, relevance, group) in enumerate(selections, start=1):
            source_path = source / "corpus" / candidate_id
            source_text = source_path.read_text(encoding="utf-8")
            prefix = "R" if relevance else "N"
            filename = f"{index:02d}_{prefix}_{candidate_id}.pdf"
            build_pdf(source_text, cv_dir / filename)
            records.append(
                {
                    "filename": filename,
                    "candidate_id": candidate_id,
                    "display_name": _first_nonempty_line(source_text),
                    "expected_relevance": relevance,
                    "group": group,
                    "source_text_sha256": sha256_file(source_path),
                }
            )

        request = build_case_request(
            offer,
            list(job["criteria"]),
            categoria="",
            stack="",
            strictness="normal",
            balance=0.5,
        )
        (case_dir / "offer.txt").write_text(offer, encoding="utf-8")
        (case_dir / "request.json").write_text(
            json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        truth = {
            "schema_version": "1.0",
            "case_id": case_id,
            "suite_id": "talentclef-20-v1",
            "source": {
                "name": "TalentCLEF 2026 Task A development/es",
                "url": SOURCE_URL,
                "license": "CC BY 4.0",
            },
            "query_id": query_id,
            "title": job["title"],
            "seed": seed,
            "selection": {
                "rule": "hasta 10 positivos qrels reproducibles y hard negatives mejor puntuados por baseline hasta completar 20",
                "positive_count": len(positives),
                "hard_negative_count": len(negatives),
                "positive_shortfall": shortfall,
                "hard_negative_source_run_id": hard_pool.get("source_run_id"),
            },
            "criteria_catalog": {
                "path": str(catalog_path.relative_to(REPO_ROOT)),
                "sha256": sha256_file(catalog_path),
                "criteria_version": "1.0",
            },
            "balance": 0.5,
            "strictness": "normal",
            "candidates": records,
        }
        (case_dir / "ground_truth.json").write_text(
            json.dumps(truth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        case_entries.append(
            {
                "case_id": case_id,
                "query_id": query_id,
                "title": job["title"],
                "path": case_id,
                "positive_count": len(positives),
                "hard_negative_count": len(negatives),
                "positive_shortfall": shortfall,
            }
        )

    output.mkdir(parents=True, exist_ok=True)
    suite_manifest = {
        "schema_version": "1.0",
        "suite_id": "talentclef-20-v1",
        "description": "Diez ofertas TalentCLEF, 20 CV PDF por oferta y criterios confirmados v1.",
        "seed": seed,
        "candidate_count": sum(
            row["positive_count"] + row["hard_negative_count"] for row in case_entries
        ),
        "source_run_id": hard_pool.get("source_run_id"),
        "criteria_catalog_sha256": sha256_file(catalog_path),
        "cases": case_entries,
        "known_exceptions": [
            {
                "query_id": row["query_id"],
                "reason": "El qrels solo contiene 8 positivos unicos; se usan 12 hard negatives.",
            }
            for row in case_entries
            if row["positive_shortfall"]
        ],
    }
    manifest_path = output / "suite_manifest.json"
    manifest_path.write_text(
        json.dumps(suite_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--criteria", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--hard-pool", type=Path, default=DEFAULT_HARD_POOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    manifest_path = generate_suite(
        args.source, args.criteria, args.hard_pool, args.output, seed=args.seed
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "cases": len(manifest["cases"]),
                "candidates": manifest["candidate_count"],
                "known_exceptions": manifest["known_exceptions"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
