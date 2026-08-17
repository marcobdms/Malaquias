"""Crea un caso manual de 20 PDF desde el corpus publico TalentCLEF."""

from __future__ import annotations

import argparse
import csv
from html import escape
import json
from pathlib import Path
import random
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.case_contract import build_case_request  # noqa: E402


DEFAULT_SOURCE = (
    REPO_ROOT
    / "benchmark/data/downloaded/talentclef_2026_task_a/extracted/TaskA/development/es"
)
DEFAULT_OUTPUT = REPO_ROOT / "benchmark/results/manual_cases/talentclef-75767-20"
SOURCE_URL = "https://zenodo.org/records/19652670"

CRITERIA = [
    {
        "id": "c1",
        "label": "Diseño y optimización de sistemas HVAC",
        "priority": "required",
        "equivalences": ["calefacción, ventilación y aire acondicionado"],
    },
    {
        "id": "c2",
        "label": "Fundamentos de ingeniería mecánica",
        "priority": "required",
        "equivalences": [],
    },
    {
        "id": "c3",
        "label": "Ingeniería de servicios de edificación",
        "priority": "important",
        "equivalences": ["building services"],
    },
    {
        "id": "c4",
        "label": "Diseño técnico, cálculos y documentación",
        "priority": "important",
        "equivalences": [],
    },
    {
        "id": "c5",
        "label": "Centros de datos o entornos críticos",
        "priority": "preferred",
        "equivalences": [],
    },
    {
        "id": "c6",
        "label": "Licencia profesional",
        "priority": "preferred",
        "equivalences": [],
    },
    {
        "id": "c7",
        "label": "Disponibilidad para viajar",
        "priority": "not_evaluable",
        "equivalences": [],
    },
]


def read_positive_ids(qrels_path: Path, query_id: str) -> list[str]:
    positives: list[str] = []
    with qrels_path.open(encoding="utf-8", newline="") as handle:
        for qid, _, candidate_id, relevance in csv.reader(handle, delimiter="\t"):
            if qid == query_id and float(relevance) > 0:
                positives.append(candidate_id)
    return sorted(set(positives))


def hard_negatives(result_path: Path, query_id: str, positives: set[str], count: int) -> list[str]:
    report = json.loads(result_path.read_text(encoding="utf-8"))
    query = next(item for item in report["queries"] if str(item["query_id"]) == query_id)
    candidates = [
        str(row["candidate_id"])
        for row in query["ranking"]
        if str(row["candidate_id"]) not in positives and float(row.get("relevance", 0)) <= 0
    ]
    if len(candidates) < count:
        raise ValueError("El baseline no contiene suficientes negativos")
    return candidates[:count]


def build_pdf(text: str, target: Path) -> None:
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "BenchmarkArial"
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
    SimpleDocTemplate(str(target), pagesize=A4, title=target.stem).build(story)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--query-id", default="75767")
    parser.add_argument("--seed", type=int, default=20260811)
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    cv_dir = output / "cvs"
    cv_dir.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("BenchmarkArial", "C:/Windows/Fonts/arial.ttf"))

    positives = read_positive_ids(source / "qrels.tsv", args.query_id)
    rng = random.Random(args.seed)
    selected_positive = sorted(rng.sample(positives, 10))
    selected_negative = hard_negatives(
        args.baseline.resolve(), args.query_id, set(positives), 10
    )

    records = []
    selections = [(candidate_id, 1, "relevant") for candidate_id in selected_positive]
    selections += [(candidate_id, 0, "hard_negative") for candidate_id in selected_negative]
    for index, (candidate_id, relevance, group) in enumerate(selections, start=1):
        source_text = (source / "corpus" / candidate_id).read_text(encoding="utf-8")
        prefix = "R" if relevance else "N"
        filename = f"{index:02d}_{prefix}_{candidate_id}.pdf"
        build_pdf(source_text, cv_dir / filename)
        records.append(
            {
                "filename": filename,
                "candidate_id": candidate_id,
                "display_name": next(line for line in source_text.splitlines() if line.strip()),
                "expected_relevance": relevance,
                "group": group,
            }
        )

    offer = (source / "queries" / args.query_id).read_text(encoding="utf-8")
    (output / "offer.txt").write_text(offer, encoding="utf-8")
    request = build_case_request(
        offer,
        CRITERIA,
        categoria="",
        stack="",
        strictness="normal",
        balance=0.5,
    )
    (output / "criteria.json").write_text(
        json.dumps(CRITERIA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "schema_version": "1.0",
        "case_id": "talentclef-75767-20",
        "source": {"name": "TalentCLEF 2026 Task A", "url": SOURCE_URL, "license": "CC BY 4.0"},
        "query_id": args.query_id,
        "seed": args.seed,
        "selection": "10 positivos aleatorios reproducibles y 10 negativos difíciles del baseline",
        "balance": 0.5,
        "strictness": "normal",
        "candidates": records,
    }
    (output / "ground_truth.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(
        "# Prueba manual TalentCLEF 75767 - 20 CV\n\n"
        "1. Copia `offer.txt` en la descripción de la vacante.\n"
        "2. Crea los siete criterios de `criteria.json` con las prioridades indicadas.\n"
        "3. Mantén balance 50 y severidad normal.\n"
        "   `request.json` conserva exactamente estos inputs para los runners.\n"
        "4. Sube juntos los 20 PDF de `cvs/`.\n"
        "5. Compara el ranking con `engine_result.json` y `ground_truth.json`.\n\n"
        "Los textos proceden del corpus público TalentCLEF; los PDF solo cambian el formato.\n",
        encoding="utf-8",
    )
    print(f"Caso creado: {output}")
    print(f"PDF: {len(records)} (relevantes=10, negativos_dificiles=10)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
