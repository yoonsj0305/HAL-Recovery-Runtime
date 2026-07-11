"""Build a bounded, non-certifying evidence bundle from Runtime artifacts."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .event_log import write_json
from .evidence_collector import collect_evidence
from .evidence_models import EvidenceBuildOutcome
from .evidence_report import build_bundle, build_manifest, build_report
from .evidence_trace import write_evidence_trace
from .evidence_validator import validate_collected_evidence


def build_evidence_bundle(
    source_directory: str | Path, output_directory: str | Path
) -> EvidenceBuildOutcome:
    collection = collect_evidence(source_directory)
    check = validate_collected_evidence(collection)
    output = Path(output_directory)
    artifact_output = output / "artifacts"
    artifact_output.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = [
        {"event_type": "evidence_build_started", "status": "ok"}
    ]
    for artifact in collection.artifacts:
        events.extend(
            (
                {
                    "event_type": "artifact_discovered",
                    "status": "ok",
                    "artifact_name": artifact.artifact_name,
                },
                {
                    "event_type": "artifact_hash_computed",
                    "status": "ok",
                    "artifact_name": artifact.artifact_name,
                    "hash_algorithm": "sha256",
                },
            )
        )
        shutil.copy2(artifact.source_path, artifact_output / artifact.artifact_name)
    for name in collection.missing_required_artifacts:
        events.append(
            {
                "event_type": "evidence_required_artifact_missing",
                "status": "invalid",
                "artifact_name": name,
            }
        )
    for reason in check.evidence_validation_reasons:
        if reason.startswith("invalid_json:"):
            events.append(
                {
                    "event_type": "evidence_artifact_json_invalid",
                    "status": "invalid",
                    "artifact_name": reason.split(":", 1)[1],
                }
            )
    for warning in check.evidence_warning_reasons:
        events.append(
            {
                "event_type": "evidence_warning_detected",
                "status": "warning",
                "reason": warning,
            }
        )
    for reason in check.safety_boundary_violations:
        events.append(
            {
                "event_type": "evidence_safety_boundary_violation",
                "status": "blocked",
                "reason": reason,
            }
        )
    manifest = build_manifest(collection)
    bundle = build_bundle(collection, check)
    report = build_report(collection, check, bundle)
    events.extend(
        (
            {"event_type": "evidence_manifest_built", "status": "ok"},
            {
                "event_type": "evidence_consistency_checked",
                "status": "ok" if check.validation_passed else "invalid",
            },
            {
                "event_type": (
                    "evidence_validation_completed"
                    if check.validation_passed
                    else "evidence_validation_failed"
                ),
                "status": check.validation_status,
            },
            {
                "event_type": "evidence_bundle_built",
                "status": "ok" if check.validation_passed else "invalid",
            },
        )
    )
    write_json(output / "evidence_manifest.json", manifest)
    write_json(output / "evidence_bundle.json", bundle)
    write_json(output / "evidence_report.json", report)
    write_evidence_trace(output / "evidence_trace.jsonl", events)
    return EvidenceBuildOutcome(manifest, bundle, report, tuple(events))
