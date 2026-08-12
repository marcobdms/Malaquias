"""Descarga snapshots reproducibles de las fuentes públicas del benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BENCHMARK_DIR = Path(__file__).resolve().parents[1]
SOURCES_FILE = BENCHMARK_DIR / "sources.json"
DOWNLOAD_DIR = BENCHMARK_DIR / "data" / "downloaded"


def load_sources() -> dict[str, dict]:
    payload = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {source["id"]: source for source in payload["sources"]}


def download(source: dict) -> Path:
    if not source.get("automatic_download"):
        raise ValueError(
            f"{source['id']} requiere una descarga manual. Consulta benchmark/sources.json."
        )

    request = Request(
        source["url"],
        headers={"User-Agent": "MalaquiasBenchmark/2.0 (+https://github.com/marcobdms/Malaquias)"},
    )
    with urlopen(request, timeout=60) as response:
        content = response.read()
        content_type = response.headers.get("Content-Type")

    retrieved_at = datetime.now(timezone.utc)
    stamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    extension = {"json": "json", "rss": "xml", "xml": "xml", "zip": "zip"}.get(
        source.get("format"), "bin"
    )
    target_dir = DOWNLOAD_DIR / source["id"]
    target_dir.mkdir(parents=True, exist_ok=True)
    data_path = target_dir / f"{stamp}.{extension}"
    data_path.write_bytes(content)

    metadata = {
        "source_id": source["id"],
        "source_url": source["url"],
        "license": source.get("license"),
        "retrieved_at": retrieved_at.isoformat(),
        "content_type": content_type,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "file": data_path.name,
    }
    metadata_path = target_dir / f"{stamp}.metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return data_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_ids", nargs="*", help="Identificadores definidos en sources.json")
    parser.add_argument("--list", action="store_true", help="Lista las fuentes disponibles")
    args = parser.parse_args()

    sources = load_sources()
    if args.list:
        for source in sources.values():
            mode = "automática" if source.get("automatic_download") else "manual"
            print(f"{source['id']}: {source['name']} ({mode})")
        return

    if not args.source_ids:
        parser.error("indica al menos una fuente o usa --list")

    for source_id in args.source_ids:
        if source_id not in sources:
            parser.error(f"fuente desconocida: {source_id}")
        path = download(sources[source_id])
        print(f"Descargado {source_id} en {path}")


if __name__ == "__main__":
    main()
