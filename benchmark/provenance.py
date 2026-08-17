"""Captura de procedencia para comparar ejecuciones meses despues."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(paths: tuple[Path, ...]) -> str:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(path.rglob("*"))
        else:
            files.append(path)
    files = sorted((path for path in files if path.is_file()), key=lambda p: str(p))
    digest = hashlib.sha256()
    common = Path(os.path.commonpath([str(path) for path in files])) if files else Path(".")
    if common.is_file():
        common = common.parent
    for path in files:
        digest.update(path.relative_to(common).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def git_metadata(repo_root: Path) -> dict[str, str | bool | None]:
    def run(*args: str) -> str | None:
        completed = subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, text=True, check=False
        )
        return completed.stdout.strip() if completed.returncode == 0 else None

    status = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(status) if status is not None else None,
    }


def canonical_hash(payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
