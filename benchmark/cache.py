"""Cache SQLite local para embeddings; nunca se versiona con el dataset."""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from pathlib import Path

import numpy as np


def text_key(model_id: str, text: str) -> str:
    payload = f"{model_id}\0{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class EmbeddingCache:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS embeddings (
                cache_key TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                vector BLOB NOT NULL
            )"""
        )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "EmbeddingCache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_many(self, model_id: str, texts: Iterable[str]) -> dict[str, np.ndarray]:
        keys = [text_key(model_id, text) for text in texts]
        if not keys:
            return {}
        result: dict[str, np.ndarray] = {}
        for offset in range(0, len(keys), 900):
            batch = keys[offset : offset + 900]
            placeholders = ",".join("?" for _ in batch)
            rows = self.connection.execute(
                f"SELECT cache_key, dimensions, vector FROM embeddings "
                f"WHERE cache_key IN ({placeholders})", batch
            )
            for key, dimensions, blob in rows:
                result[key] = np.frombuffer(blob, dtype=np.float32, count=dimensions).copy()
        return result

    def put_many(self, model_id: str, items: Iterable[tuple[str, np.ndarray]]) -> None:
        rows = []
        for text, vector in items:
            normalized = np.asarray(vector, dtype=np.float32).reshape(-1)
            rows.append(
                (text_key(model_id, text), model_id, int(normalized.shape[0]), normalized.tobytes())
            )
        self.connection.executemany(
            "INSERT OR REPLACE INTO embeddings "
            "(cache_key, model_id, dimensions, vector) VALUES (?, ?, ?, ?)", rows
        )
        self.connection.commit()


def encode_with_cache(
    encoder: object,
    model_id: str,
    texts: Iterable[str],
    cache: EmbeddingCache,
    batch_size: int,
) -> tuple[np.ndarray, dict[str, int]]:
    ordered = list(texts)
    cached = cache.get_many(model_id, ordered)
    missing_texts = list(
        dict.fromkeys(text for text in ordered if text_key(model_id, text) not in cached)
    )
    if missing_texts:
        vectors = encoder.encode(
            missing_texts,
            batch_size=batch_size,
            show_progress_bar=len(missing_texts) > batch_size,
            convert_to_numpy=True,
        )
        cache.put_many(model_id, zip(missing_texts, vectors, strict=True))
        cached.update(cache.get_many(model_id, missing_texts))
    matrix = np.stack([cached[text_key(model_id, text)] for text in ordered])
    return matrix, {"hits": len(ordered) - len(missing_texts), "misses": len(missing_texts)}
