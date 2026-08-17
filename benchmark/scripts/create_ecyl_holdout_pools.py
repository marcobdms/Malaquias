"""Congela pools candidatos ECYL x TalentCLEF sin crear etiquetas de relevancia.

La seleccion usa exclusivamente el baseline historico sobre el texto bruto de
la oferta. No importa criterios experimentales ni ``lexical_v2``. Los PDF son
una representacion reproducible del texto fuente y nunca la fuente canonica.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from html import escape
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.cache import EmbeddingCache, encode_with_cache  # noqa: E402
from benchmark.provenance import canonical_hash, sha256_file, sha256_tree  # noqa: E402
from benchmark.runner import load_encoder  # noqa: E402
from benchmark.scoring import rank_pool  # noqa: E402


DEFAULT_JOBS = REPO_ROOT / "benchmark/catalogs/ecyl-pilot-jobs.json"
DEFAULT_CORPUS = (
    REPO_ROOT
    / "benchmark/data/downloaded/talentclef_2026_task_a/extracted/TaskA/development/es/corpus"
)
DEFAULT_CONFIG = REPO_ROOT / "benchmark/configs/baseline.json"
DEFAULT_POOL = REPO_ROOT / "benchmark/pools/ecyl-talentclef-unjudged-20-v1.json"
DEFAULT_MANIFEST = REPO_ROOT / "benchmark/manifests/ecyl-talentclef-holdout-candidate-v1.json"
DEFAULT_MATERIAL = REPO_ROOT / "benchmark/results/holdout_candidates/ecyl-talentclef-unjudged-20-v1"
DEFAULT_CACHE = REPO_ROOT / "benchmark/results/cache/embeddings.sqlite3"
DEFAULT_SEED = 20260816

PRIORITY_REVIEW_IDS = {
    "ecyl-1285669061147": "ciberseguridad_it",
    "ecyl-1285665706767": "comercial_ventas",
    "ecyl-1285667274695": "logistica_carretilla",
}


def stable_job_seed(seed: int, job_id: str) -> int:
    digest = hashlib.sha256(job_id.encode("utf-8")).hexdigest()
    return seed + int(digest[:8], 16)


def select_stratified_pool(
    ranking: Iterable[dict[str, Any]],
    *,
    job_id: str,
    seed: int,
    top_count: int = 8,
    adjacent_count: int = 6,
    random_count: int = 6,
    adjacent_rank_end: int = 60,
) -> list[dict[str, Any]]:
    """Mezcla top, candidatos cercanos y cola aleatoria sin inferir etiquetas."""

    rows = list(ranking)
    ids = [str(row["candidate_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("El ranking de entrada contiene candidatos duplicados")
    total = top_count + adjacent_count + random_count
    if len(rows) < total or adjacent_rank_end < top_count + adjacent_count:
        raise ValueError("El ranking no permite construir las tres franjas solicitadas")
    if len(rows) - adjacent_rank_end < random_count:
        raise ValueError("No hay suficientes candidatos en la cola aleatoria")

    rng = random.Random(stable_job_seed(seed, job_id))
    ranked = [{**row, "baseline_rank": index} for index, row in enumerate(rows, start=1)]
    top = ranked[:top_count]
    adjacent = sorted(
        rng.sample(ranked[top_count:adjacent_rank_end], adjacent_count),
        key=lambda row: int(row["baseline_rank"]),
    )
    random_tail = sorted(
        rng.sample(ranked[adjacent_rank_end:], random_count),
        key=lambda row: int(row["baseline_rank"]),
    )

    selected: list[dict[str, Any]] = []
    for group, group_rows in (
        ("baseline_top", top),
        ("baseline_adjacent", adjacent),
        ("seeded_random_tail", random_tail),
    ):
        for row in group_rows:
            selected.append({**row, "selection_group": group})
    if len(selected) != total or len({row["candidate_id"] for row in selected}) != total:
        raise AssertionError("La seleccion estratificada debe contener candidatos unicos")
    return selected


def _load_corpus(corpus_dir: Path) -> tuple[list[str], list[str], list[Path]]:
    paths = sorted((path for path in corpus_dir.iterdir() if path.is_file()), key=lambda p: p.name)
    if not paths:
        raise FileNotFoundError(f"No hay perfiles en {corpus_dir}")
    return [path.name for path in paths], [path.read_text(encoding="utf-8") for path in paths], paths


def build_pdf(text: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    story = []
    for block in text.split("\n\n"):
        block = block.strip()
        if block:
            story.extend(
                [
                    Paragraph(escape(block).replace("\n", "<br/>"), styles["BodyText"]),
                    Spacer(1, 8),
                ]
            )
    SimpleDocTemplate(
        str(target), pagesize=A4, title=target.stem, author="TalentCLEF", invariant=1
    ).build(story)


def _rank_jobs(
    jobs: list[dict[str, Any]],
    candidate_ids: list[str],
    candidate_texts: list[str],
    config: dict[str, Any],
    cache_path: Path,
    *,
    encoder: object | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Aplica el baseline v1 existente al raw_text; no calcula ninguna metrica."""

    model_id = str(config["model_id"])
    active_encoder = encoder or load_encoder(model_id)
    job_texts = [str(job["raw_text"]) for job in jobs]
    all_texts = job_texts + candidate_texts
    with EmbeddingCache(cache_path) as cache:
        vectors, _ = encode_with_cache(
            active_encoder,
            model_id,
            all_texts,
            cache,
            int(config.get("batch_size", 32)),
        )
    job_vectors = vectors[: len(job_texts)]
    candidate_vectors = vectors[len(job_texts) :]
    rankings: dict[str, list[dict[str, Any]]] = {}
    for job, vector in zip(jobs, job_vectors, strict=True):
        rankings[str(job["id"])] = rank_pool(
            str(job["raw_text"]),
            candidate_ids,
            candidate_texts,
            np.asarray(vector),
            candidate_vectors,
            balance=float(config["balance"]),
            strictness=str(config["strictness"]),
            keyword_multiplier=float(config.get("keyword_multiplier", 2.5)),
        )
    return rankings


def _candidate_record(
    row: dict[str, Any], source_path: Path, pdf_path: Path, material_root: Path
) -> dict[str, Any]:
    return {
        "candidate_id": str(row["candidate_id"]),
        "status": "incoming_unjudged",
        "relevance": "unknown",
        "selection_group": row["selection_group"],
        "selection_baseline": {
            "rank": int(row["baseline_rank"]),
            "score": float(row["score"]),
            "semantic_score": float(row["semantic_score"]),
            "keyword_score": float(row["keyword_score"]),
        },
        "canonical_source": {
            "kind": "talentclef_text_profile",
            "relative_path": source_path.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(source_path),
        },
        "pdf_representation": {
            "relative_path": pdf_path.relative_to(REPO_ROOT).as_posix(),
            "path_within_material": pdf_path.relative_to(material_root).as_posix(),
            "sha256": sha256_file(pdf_path),
            "canonical": False,
            "note": "PDF generado sin alterar el texto; el TXT de TalentCLEF es la fuente canonica.",
        },
    }


def validate_pool_payload(payload: dict[str, Any]) -> None:
    if payload.get("benchmark_status") != "incoming_unjudged":
        raise ValueError("El conjunto debe permanecer incoming_unjudged")
    pools = payload.get("pools", [])
    if len(pools) != 9:
        raise ValueError("Deben existir exactamente nueve pools ECYL")
    priority = 0
    for pool in pools:
        candidates = pool.get("candidates", [])
        ids = [row.get("candidate_id") for row in candidates]
        if len(candidates) != 20 or len(ids) != len(set(ids)):
            raise ValueError(f"Pool invalido para {pool.get('job_id')}")
        if any(row.get("relevance") != "unknown" for row in candidates):
            raise ValueError("Un pool sin adjudicar no puede contener etiquetas")
        if any("display_name" in row for row in candidates):
            raise ValueError("Los metadatos del holdout no deben duplicar nombres o PII")
        counts = {
            group: sum(row.get("selection_group") == group for row in candidates)
            for group in ("baseline_top", "baseline_adjacent", "seeded_random_tail")
        }
        if counts != {"baseline_top": 8, "baseline_adjacent": 6, "seeded_random_tail": 6}:
            raise ValueError(f"Mezcla de seleccion inesperada: {counts}")
        priority += bool(pool.get("priority_review"))
    if priority != 3:
        raise ValueError("Deben marcarse exactamente tres pools prioritarios")


def create_holdout_candidate(
    jobs_path: Path,
    corpus_dir: Path,
    config_path: Path,
    pool_path: Path,
    manifest_path: Path,
    material_root: Path,
    cache_path: Path,
    *,
    seed: int = DEFAULT_SEED,
    encoder: object | None = None,
) -> tuple[Path, Path]:
    jobs_payload = json.loads(jobs_path.read_text(encoding="utf-8"))
    jobs = list(jobs_payload["jobs"])
    if len(jobs) != 9:
        raise ValueError("El catalogo ECYL debe contener exactamente nueve ofertas")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    candidate_ids, candidate_texts, corpus_paths = _load_corpus(corpus_dir)
    rankings = _rank_jobs(
        jobs, candidate_ids, candidate_texts, config, cache_path, encoder=encoder
    )
    source_by_id = dict(zip(candidate_ids, corpus_paths, strict=True))

    pools = []
    for job in jobs:
        job_id = str(job["id"])
        selected = select_stratified_pool(rankings[job_id], job_id=job_id, seed=seed)
        case_dir = material_root / job_id
        (case_dir / "cvs").mkdir(parents=True, exist_ok=True)
        offer_path = case_dir / "offer.txt"
        offer_path.write_text(str(job["raw_text"]), encoding="utf-8")
        records = []
        for index, row in enumerate(selected, start=1):
            candidate_id = str(row["candidate_id"])
            source_path = source_by_id[candidate_id]
            pdf_path = case_dir / "cvs" / f"{index:02d}_{candidate_id}.pdf"
            build_pdf(source_path.read_text(encoding="utf-8"), pdf_path)
            records.append(_candidate_record(row, source_path, pdf_path, material_root))
        priority_key = PRIORITY_REVIEW_IDS.get(job_id)
        pools.append(
            {
                "pool_id": f"{job_id}-20",
                "job_id": job_id,
                "title": job["title"],
                "professional_family": job["professional_family"],
                "status": "incoming_unjudged",
                "priority_review": priority_key is not None,
                "priority_review_track": priority_key,
                "job_source": job["source"],
                "job_text_sha256": job["raw_text_sha256"],
                "offer_representation": {
                    "relative_path": offer_path.relative_to(REPO_ROOT).as_posix(),
                    "sha256": sha256_file(offer_path),
                    "canonical": False,
                },
                "candidate_count": len(records),
                "candidates": records,
            }
        )

    payload = {
        "schema_version": "1.0",
        "id": "ecyl-talentclef-unjudged-20-v1",
        "benchmark_status": "incoming_unjudged",
        "gold_set": False,
        "seed": seed,
        "purpose": "Pools candidatos para futura revision humana; prohibido calibrar o reportar metricas con ellos.",
        "selection": {
            "method": "baseline_hybrid_v1_raw_offer",
            "rule": "8 primeros + 6 muestreados de ranks 9-60 + 6 aleatorios de ranks 61-472",
            "uses_job_criteria": False,
            "uses_lexical_v2": False,
            "uses_labels": False,
            "config_path": config_path.relative_to(REPO_ROOT).as_posix(),
            "config_sha256": sha256_file(config_path),
            "config": config,
        },
        "sources": {
            "jobs": {
                "name": "Ofertas de empleo de Castilla y Leon (ECYL)",
                "source_url": "https://datosabiertos.jcyl.es/web/jcyl/risp/es/empleo/ofertas-empleo/1284354353012.json",
                "license": "CC BY 4.0 ES",
                "catalog_path": jobs_path.relative_to(REPO_ROOT).as_posix(),
                "catalog_sha256": sha256_file(jobs_path),
                "snapshot_sha256": jobs_payload["source_snapshot_sha256"],
            },
            "candidates": {
                "name": "TalentCLEF 2026 Task A development/es",
                "source_url": "https://zenodo.org/records/19652670",
                "license": "CC BY 4.0",
                "market": "multilingual; no representa especificamente Espana",
                "corpus_path": corpus_dir.relative_to(REPO_ROOT).as_posix(),
                "corpus_file_count": len(candidate_ids),
                "corpus_sha256": sha256_tree((corpus_dir,)),
            },
        },
        "material": {
            "root": material_root.relative_to(REPO_ROOT).as_posix(),
            "git_ignored": True,
            "pdf_policy": "Representacion para probar el parser/UI; el texto fuente y su hash son canonicos.",
        },
        "pools": pools,
    }
    validate_pool_payload(payload)
    pool_path.parent.mkdir(parents=True, exist_ok=True)
    pool_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": "1.0",
        "id": "ecyl-talentclef-holdout-candidate-v1",
        "split": "candidate_holdout",
        "status": "incoming_unjudged",
        "gold_set": False,
        "sealed_for_scoring": True,
        "pool_path": pool_path.relative_to(REPO_ROOT).as_posix(),
        "pool_sha256": sha256_file(pool_path),
        "pool_count": 9,
        "candidates_per_pool": 20,
        "priority_review_tracks": list(PRIORITY_REVIEW_IDS.values()),
        "allowed_next_action": "human_adjudication",
        "prohibited_until_adjudicated": [
            "calibration",
            "metric_reporting",
            "experimental_variant_execution",
            "gold_set_claim",
        ],
        "identity_sha256": canonical_hash(
            {
                "pool_sha256": sha256_file(pool_path),
                "seed": seed,
                "selection": payload["selection"],
            }
        ),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return pool_path, manifest_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=DEFAULT_JOBS)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--material-root", type=Path, default=DEFAULT_MATERIAL)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)
    pool, manifest = create_holdout_candidate(
        args.jobs.resolve(),
        args.corpus.resolve(),
        args.config.resolve(),
        args.pool.resolve(),
        args.manifest.resolve(),
        args.material_root.resolve(),
        args.cache.resolve(),
        seed=args.seed,
    )
    print(json.dumps({"pool": str(pool), "manifest": str(manifest)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
