"""Artifact indexing for pipeline-generated files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidence_hasher import sha256_file
from .evidence_schema import ARTIFACT_TYPES
from .pipeline_models import PIPELINE_ID, boundary_fields


PIPELINE_ROOT_ARTIFACTS = {
    "pipeline_trace.jsonl",
    "pipeline_summary.json",
    "pipeline_report.json",
}
PIPELINE_SUBDIR_ARTIFACTS = {
    "runtime/runtime_plan.json",
    "runtime/runtime_report.json",
    "runtime/runtime_events.jsonl",
    "adapter/adapter_report.json",
    "adapter/adapter_trace.jsonl",
    "failure/failure_trace.jsonl",
    "failure/rollback_plan.json",
    "failure/rollback_report.json",
    "policy/policy_trace.jsonl",
    "policy/policy_decision.json",
    "policy/policy_report.json",
    "evidence/evidence_manifest.json",
    "evidence/evidence_bundle.json",
    "evidence/evidence_report.json",
    "evidence/evidence_trace.jsonl",
}


def build_pipeline_artifact_index(output_directory: str | Path) -> dict[str, Any]:
    root = Path(output_directory)
    artifacts: list[dict[str, Any]] = []
    recognized = PIPELINE_ROOT_ARTIFACTS | PIPELINE_SUBDIR_ARTIFACTS
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        relative_path = relative.as_posix()
        if relative_path == "pipeline_artifact_index.json":
            continue
        if relative_path not in recognized and not _is_evidence_artifact(relative_path):
            continue
        artifacts.append(
            {
                "stage_name": _stage_name(relative_path),
                "artifact_name": path.name,
                "relative_path": relative_path,
                "present": True,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return {
        **boundary_fields(),
        "pipeline_id": PIPELINE_ID,
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "hash_algorithm": "sha256",
    }


def _is_evidence_artifact(relative_path: str) -> bool:
    prefix = "evidence/artifacts/"
    if not relative_path.startswith(prefix):
        return False
    return relative_path.removeprefix(prefix) in ARTIFACT_TYPES


def _stage_name(relative_path: str) -> str:
    if relative_path.startswith("runtime/"):
        return "runtime_dry_run"
    if relative_path.startswith("adapter/"):
        return "adapter_simulation"
    if relative_path.startswith("failure/"):
        return "failure_rollback_simulation"
    if relative_path.startswith("policy/"):
        return "policy_simulation"
    if relative_path.startswith("evidence/"):
        return "evidence_bundle"
    return "pipeline_report"
