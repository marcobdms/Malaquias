"""Normaliza una seleccion trazable de ofertas ECYL para futuros pools espanoles."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path


def repair_encoding(value: str) -> str:
    for _ in range(2):
        if not any(marker in value for marker in ("Ã", "Â", "â")):
            break
        try:
            value = value.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
    return value


def clean_html(value: str) -> str:
    text = re.sub(r"(?i)<br\s*/?>|</p>|</li>", "\n", value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = repair_encoding(html.unescape(text))
    text = re.split(r"(?i)\n\s*Para participar\s*:", text, maxsplit=1)[0]
    lines = [re.sub(r"\s+", " ", line).strip(" -") for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def attributes(record: dict) -> dict[str, object]:
    result = {}
    for item in record.get("attribute", []):
        result[item["name"]] = item.get("text") or item.get("date") or item.get("valor")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    snapshot_path = (args.selection.parent / selection["source_snapshot"]).resolve()
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    records = [item["element"] for item in payload["document"]["list"]]
    by_id = {}
    for record in records:
        data = attributes(record)
        by_id[str(data.get("Identificador"))] = data

    jobs = []
    for chosen in selection["jobs"]:
        source = by_id.get(chosen["id"])
        if source is None:
            raise ValueError(f"No existe la oferta ECYL {chosen['id']}")
        raw_text = clean_html(str(source.get("Descripcion_es") or ""))
        province = source.get("Provincia") or []
        location = province[0].get("string") if isinstance(province, list) and province else None
        jobs.append({
            "schema_version": "1.0",
            "id": f"ecyl-{chosen['id']}",
            "title": repair_encoding(str(source.get("Titulo_es") or chosen["id"])),
            "language": "es",
            "location": location,
            "professional_family": chosen["professional_family"],
            "source": {
                "source_id": selection["source_id"],
                "source_url": source.get("Enlace al contenido"),
                "captured_at": selection["captured_at"],
                "license": selection["license"],
            },
            "published_at": source.get("FechaPublicacion"),
            "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
            "raw_text": raw_text,
            "criteria": [],
            "benchmark_status": "input_only_unjudged",
        })

    output = {
        "schema_version": "1.0",
        "id": "ecyl-pilot-jobs-20260810",
        "purpose": "Spanish input catalogue; not a gold set and not used for metrics yet.",
        "source_snapshot_sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "jobs": jobs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Catalogo: {args.output} ({len(jobs)} vacantes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
