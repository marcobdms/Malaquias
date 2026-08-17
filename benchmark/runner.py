"""Ejecuta un benchmark de ranking reproducible sin llamar a ningun LLM."""

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from benchmark.cache import EmbeddingCache, encode_with_cache
from benchmark.loaders import load_dataset, load_json
from benchmark.metrics import evaluate_ranking, macro_average
from benchmark.provenance import canonical_hash, git_metadata, sha256_file, sha256_tree
from benchmark.scoring import chunk_text, rank_pool, rank_pool_chunked


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = Path(__file__).resolve().parent / "results"


def load_encoder(model_id: str) -> object:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_id)


def compare_baseline(current: dict[str, float], baseline_path: Path | None) -> dict | None:
    if baseline_path is None:
        return None
    baseline = load_json(baseline_path)
    previous = baseline.get("metrics", {}).get("macro", {})
    common = sorted(set(current) & set(previous))
    return {
        "path": str(baseline_path),
        "run_id": baseline.get("run_id"),
        "delta": {key: round(current[key] - float(previous[key]), 8) for key in common},
    }


def run_benchmark(
    manifest_path: Path,
    config_path: Path,
    output_dir: Path,
    *,
    baseline_path: Path | None = None,
    max_queries: int | None = None,
    encoder: object | None = None,
) -> tuple[dict, Path]:
    manifest_path = manifest_path.resolve()
    config_path = config_path.resolve()
    config = load_json(config_path)
    seed = int(config["seed"])
    random.seed(seed)
    np.random.seed(seed)
    manifest, dataset = load_dataset(manifest_path, seed)
    pools = list(dataset.pools)
    if max_queries is not None:
        if max_queries < 1:
            raise ValueError("max_queries debe ser positivo")
        pools = pools[:max_queries]

    model_id = config["model_id"]
    active_encoder = encoder or load_encoder(model_id)
    unique_candidate_ids = sorted({candidate for pool in pools for candidate in pool.candidate_ids})
    query_texts = [pool.query_text for pool in pools]
    candidate_texts = [dataset.corpus[candidate_id] for candidate_id in unique_candidate_ids]
    chunk_tokens = config.get("chunk_tokens")
    chunk_overlap = int(config.get("chunk_overlap", 0))
    if chunk_tokens:
        query_groups = [chunk_text(text, int(chunk_tokens), chunk_overlap) for text in query_texts]
        candidate_groups = [chunk_text(text, int(chunk_tokens), chunk_overlap) for text in candidate_texts]
        all_texts = [text for group in query_groups + candidate_groups for text in group]
    else:
        query_groups = [[text] for text in query_texts]
        candidate_groups = [[text] for text in candidate_texts]
        all_texts = query_texts + candidate_texts
    cache_path = output_dir / "cache" / "embeddings.sqlite3"
    with EmbeddingCache(cache_path) as cache:
        vectors, cache_stats = encode_with_cache(
            active_encoder,
            model_id,
            all_texts,
            cache,
            int(config.get("batch_size", 32)),
        )
    group_vectors = []
    offset = 0
    for group in query_groups + candidate_groups:
        group_vectors.append(vectors[offset:offset + len(group)])
        offset += len(group)
    query_vectors = group_vectors[:len(query_groups)]
    candidate_vectors = group_vectors[len(query_groups):]
    vector_by_candidate = dict(zip(unique_candidate_ids, candidate_vectors, strict=True))

    rankings = []
    metric_rows = []
    cutoffs = [int(value) for value in config.get("cutoffs", [5, 10])]
    for pool, query_vector in zip(pools, query_vectors, strict=True):
        ids = list(pool.candidate_ids)
        texts = [dataset.corpus[candidate_id] for candidate_id in ids]
        if chunk_tokens:
            ranking = rank_pool_chunked(
                pool.query_text,
                ids,
                texts,
                query_vector,
                {candidate_id: vector_by_candidate[candidate_id] for candidate_id in ids},
                balance=float(config["balance"]),
                strictness=config["strictness"],
                keyword_multiplier=float(config.get("keyword_multiplier", 2.5)),
                semantic_top_k=int(config.get("semantic_top_k", 2)),
            )
        else:
            matrix = np.stack([vector_by_candidate[candidate_id][0] for candidate_id in ids])
            ranking = rank_pool(
                pool.query_text,
                ids,
                texts,
                query_vector[0],
                matrix,
                balance=float(config["balance"]),
                strictness=config["strictness"],
                keyword_multiplier=float(config.get("keyword_multiplier", 2.5)),
            )
        ordered_ids = [str(row["candidate_id"]) for row in ranking]
        metrics = evaluate_ranking(ordered_ids, pool.relevance, cutoffs)
        metric_rows.append(metrics)
        rankings.append({
            "query_id": pool.query_id,
            "pool_size": len(ids),
            "relevant_count": sum(float(value) > 0 for value in pool.relevance.values()),
            "metrics": {key: round(value, 8) for key, value in metrics.items()},
            "ranking": [
                {**row, "relevance": pool.relevance[str(row["candidate_id"])]}
                for row in ranking
            ],
        })

    macro = {key: round(value, 8) for key, value in macro_average(metric_rows).items()}
    now = datetime.now(timezone.utc)
    identity = {
        "manifest_hash": sha256_file(manifest_path),
        "config_hash": sha256_file(config_path),
        "dataset_hash": sha256_tree(dataset.input_paths),
        "seed": seed,
        "max_queries": max_queries,
    }
    run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{canonical_hash(identity)[:10]}"
    report = {
        "schema_version": "1.0",
        "run_id": run_id,
        "created_at": now.isoformat(),
        "task": "ranking_without_llm",
        "git": git_metadata(REPO_ROOT),
        "runtime": {"python": platform.python_version(), "platform": platform.platform()},
        "inputs": {
            "manifest": str(manifest_path),
            "config": str(config_path),
            **identity,
            "dataset_id": dataset.dataset_id,
            "source_root": str(dataset.root),
            "pool_strategy": manifest.get("pool", {}).get("strategy", "all"),
        },
        "parameters": config,
        "cache": {**cache_stats, "path": str(cache_path)},
        "metrics": {"macro": macro, "queries": len(rankings)},
        "baseline_comparison": compare_baseline(macro, baseline_path),
        "queries": rankings,
    }
    run_dir = output_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    result_path = run_dir / "result.json"
    result_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary_path = run_dir / "summary.md"
    lines = [
        f"# Benchmark {run_id}", "",
        f"- Dataset: `{dataset.dataset_id}`",
        f"- Queries: {len(rankings)}",
        f"- Commit: `{report['git']['commit']}`",
        f"- Working tree dirty: `{report['git']['dirty']}`",
        f"- Cache: {cache_stats['hits']} hits, {cache_stats['misses']} misses",
        "", "## Metricas macro", "",
        "| Metrica | Valor | Delta baseline |", "|---|---:|---:|",
    ]
    deltas = (report["baseline_comparison"] or {}).get("delta", {})
    for key, value in macro.items():
        delta = deltas.get(key)
        if delta is None:
            lines.append(f"| {key} | {value:.4f} | - |")
        else:
            lines.append(f"| {key} | {value:.4f} | {delta:+.4f} |")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report, result_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--max-queries", type=int, help="Solo smoke tests; queda registrado")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report, path = run_benchmark(
            args.manifest,
            args.config,
            args.output_dir.resolve(),
            baseline_path=args.baseline.resolve() if args.baseline else None,
            max_queries=args.max_queries,
        )
    except (FileNotFoundError, KeyError, ValueError) as error:
        print(f"Error de configuracion: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report["metrics"]["macro"], indent=2))
    print(f"Resultado: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
