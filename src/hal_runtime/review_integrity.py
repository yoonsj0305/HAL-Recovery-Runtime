"""SHA-256 integrity evidence for local review artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .review_models import REVIEW_HASHED_FILES


def file_hash_record(path: str | Path) -> dict[str, Any]:
    artifact = Path(path)
    if not artifact.is_file():
        return {"sha256": None, "size_bytes": None, "present": False}
    payload = artifact.read_bytes()
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "present": True,
    }


def review_artifact_hashes(root: str | Path) -> dict[str, dict[str, Any]]:
    directory = Path(root)
    return {name: file_hash_record(directory / name) for name in REVIEW_HASHED_FILES}


def sha256_or_none(path: str | Path) -> str | None:
    record = file_hash_record(path)
    value = record["sha256"]
    return value if isinstance(value, str) else None
