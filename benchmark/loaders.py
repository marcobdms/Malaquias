"""Carga manifiestos de pools y adapta TalentCLEF sin copiar el corpus."""

from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class QueryPool:
    query_id: str
    query_text: str
    candidate_ids: tuple[str, ...]
    relevance: dict[str, int | float | str]


@dataclass(frozen=True)
class Dataset:
    dataset_id: str
    root: Path
    corpus: dict[str, str]
    pools: tuple[QueryPool, ...]
    input_paths: tuple[Path, ...]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_manifest_path(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (manifest_path.parent / path).resolve()


def _read_text_directory(path: Path) -> dict[str, str]:
    if not path.is_dir():
        raise FileNotFoundError(f"No existe el directorio requerido: {path}")
    return {
        item.name: item.read_text(encoding="utf-8")
        for item in sorted(path.iterdir(), key=lambda value: value.name)
        if item.is_file()
    }


def _select_pool(
    strategy: str,
    corpus_ids: list[str],
    relevance: dict[str, int],
    rng: random.Random,
    negatives_per_query: int | None,
    fixed_ids: list[str] | None = None,
) -> list[str]:
    if strategy == "all":
        return list(corpus_ids)
    positives = sorted(candidate_id for candidate_id, label in relevance.items() if label > 0)
    if strategy == "judged":
        return sorted(relevance)
    if strategy == "positives_plus_sampled_negatives":
        if negatives_per_query is None or negatives_per_query < 1:
            raise ValueError("negatives_per_query debe ser positivo para esta estrategia")
        negatives = [candidate_id for candidate_id in corpus_ids if candidate_id not in relevance]
        chosen = rng.sample(negatives, min(negatives_per_query, len(negatives)))
        return positives + chosen
    if strategy == "fixed":
        if not fixed_ids:
            raise ValueError("El pool fixed no contiene candidatos")
        unknown = sorted(set(fixed_ids) - set(corpus_ids))
        if unknown:
            raise ValueError(f"El pool fixed contiene candidatos desconocidos: {unknown[:3]}")
        return list(dict.fromkeys(fixed_ids))
    raise ValueError(f"Estrategia de pool desconocida: {strategy}")


def load_talentclef(manifest_path: Path, manifest: dict, seed: int) -> Dataset:
    source = manifest["source"]
    root = resolve_manifest_path(manifest_path, source["root"])
    queries_dir = root / source.get("queries_dir", "queries")
    corpus_dir = root / source.get("corpus_dir", "corpus")
    qrels_path = root / source.get("qrels_file", "qrels.tsv")
    queries = _read_text_directory(queries_dir)
    corpus = _read_text_directory(corpus_dir)
    relevance_by_query: dict[str, dict[str, int]] = {}
    with qrels_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row or row[0].startswith("#"):
                continue
            if len(row) != 4:
                raise ValueError(f"Fila qrels invalida: {row}")
            query_id, _, candidate_id, label = row
            relevance_by_query.setdefault(query_id, {})[candidate_id] = int(label)

    pool_config = manifest.get("pool", {"strategy": "all"})
    strategy = pool_config.get("strategy", "all")
    include_queries = manifest.get("queries", {}).get("include", sorted(queries))
    exclude_queries = set(manifest.get("queries", {}).get("exclude", []))
    rng = random.Random(seed)
    fixed_path = None
    fixed_queries = {}
    if strategy == "fixed":
        fixed_path = resolve_manifest_path(manifest_path, pool_config["ids_file"])
        fixed_payload = load_json(fixed_path)
        fixed_queries = fixed_payload.get("queries", {})
    pools = []
    for query_id in include_queries:
        if query_id in exclude_queries:
            continue
        if query_id not in queries:
            raise ValueError(f"La query {query_id} no existe en {queries_dir}")
        relevance = relevance_by_query.get(query_id, {})
        selected = _select_pool(
            strategy,
            sorted(corpus),
            relevance,
            rng,
            pool_config.get("negatives_per_query"),
            fixed_queries.get(query_id),
        )
        pools.append(QueryPool(
            query_id=query_id,
            query_text=queries[query_id],
            candidate_ids=tuple(selected),
            relevance={candidate_id: relevance.get(candidate_id, 0) for candidate_id in selected},
        ))
    if not pools:
        raise ValueError("El manifiesto no produjo ningun pool")
    return Dataset(
        dataset_id=manifest["id"],
        root=root,
        corpus=corpus,
        pools=tuple(pools),
        input_paths=(queries_dir, corpus_dir, qrels_path, *((fixed_path,) if fixed_path else ())),
    )


def load_dataset(manifest_path: Path, seed: int) -> tuple[dict, Dataset]:
    manifest = load_json(manifest_path)
    if manifest.get("schema_version") != "1.0":
        raise ValueError("schema_version de manifiesto no soportada")
    source_type = manifest.get("source", {}).get("type")
    if source_type == "talentclef":
        return manifest, load_talentclef(manifest_path, manifest, seed)
    raise ValueError(f"Tipo de fuente no soportado: {source_type}")
