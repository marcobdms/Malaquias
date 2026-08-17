"""Ejecuta varias configuraciones con un solo modelo y resume la comparacion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from benchmark.runner import load_encoder, run_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--configs", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark/results"))
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()

    configs = [json.loads(path.read_text(encoding="utf-8")) for path in args.configs]
    model_ids = {config["model_id"] for config in configs}
    if len(model_ids) != 1:
        raise ValueError("Todos los configs del grid deben usar el mismo modelo")
    encoder = load_encoder(model_ids.pop())
    rows = []
    for path, config in zip(args.configs, configs, strict=True):
        report, result_path = run_benchmark(
            args.manifest,
            path,
            args.output_dir,
            baseline_path=args.baseline,
            encoder=encoder,
        )
        rows.append({
            "config": config["name"],
            "balance": config["balance"],
            "run_id": report["run_id"],
            "result": str(result_path),
            "metrics": report["metrics"]["macro"],
        })

    rows.sort(key=lambda row: row["metrics"].get("ndcg@10", 0), reverse=True)
    grid_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    grid_dir = args.output_dir / "grids" / grid_id
    grid_dir.mkdir(parents=True, exist_ok=False)
    (grid_dir / "result.json").write_text(
        json.dumps({"grid_id": grid_id, "ranking_metric": "ndcg@10", "runs": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        f"# Grid {grid_id}", "", "Ordenado por `ndcg@10`.", "",
        "| Config | Balance lexico | P@5 | nDCG@5 | P@10 | nDCG@10 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        metrics = row["metrics"]
        lines.append(
            f"| {row['config']} | {row['balance']:.2f} | {metrics['precision@5']:.4f} | "
            f"{metrics['ndcg@5']:.4f} | {metrics['precision@10']:.4f} | {metrics['ndcg@10']:.4f} |"
        )
    (grid_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"Grid: {grid_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
