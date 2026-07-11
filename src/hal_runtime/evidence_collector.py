"""Collect only recognized, flat, size-bounded evidence artifacts."""

from __future__ import annotations

from pathlib import Path

from .evidence_hasher import hash_with_size
from .evidence_models import EvidenceArtifact, EvidenceCollection
from .evidence_schema import (
    ARTIFACT_TYPES,
    MAX_ARTIFACT_SIZE_BYTES,
    REQUIRED_ARTIFACTS,
)


class EvidenceCollectionError(ValueError):
    """Raised when an evidence input directory cannot be read."""


def collect_evidence(
    source_directory: str | Path,
    *,
    max_size_bytes: int = MAX_ARTIFACT_SIZE_BYTES,
) -> EvidenceCollection:
    source = Path(source_directory)
    if not source.is_dir():
        raise EvidenceCollectionError("evidence_source_not_directory")
    artifacts: list[EvidenceArtifact] = []
    unsupported: list[str] = []
    warnings: list[str] = []
    for path in sorted(source.iterdir(), key=lambda item: item.name):
        if path.name.startswith(".") or not path.is_file():
            continue
        if path.name not in ARTIFACT_TYPES:
            unsupported.append(path.name)
            continue
        size = path.stat().st_size
        if size > max_size_bytes:
            warnings.append(f"artifact_too_large:{path.name}")
            continue
        digest, size = hash_with_size(path)
        artifacts.append(
            EvidenceArtifact(
                artifact_name=path.name,
                artifact_type=ARTIFACT_TYPES[path.name],
                relative_path=path.name,
                sha256=digest,
                size_bytes=size,
                required=path.name in REQUIRED_ARTIFACTS,
                source_path=path,
            )
        )
    present = {artifact.artifact_name for artifact in artifacts}
    missing = tuple(name for name in REQUIRED_ARTIFACTS if name not in present)
    return EvidenceCollection(
        source_directory=source,
        artifacts=tuple(artifacts),
        missing_required_artifacts=missing,
        unsupported_artifacts=tuple(unsupported),
        warnings=tuple(warnings),
    )
