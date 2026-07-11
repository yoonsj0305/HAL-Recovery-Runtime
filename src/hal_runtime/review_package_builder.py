"""Build candidate review packages from shadow ingestion artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .event_log import write_json
from .review_decision import review_decision_template
from .review_gate import evaluate_review_gates
from .review_integrity import review_artifact_hashes
from .review_models import REVIEW_REQUIRED_FILES, review_read_only_fields
from .review_schema import review_schema_document
from .review_trace import gate_event, write_review_trace


def build_candidate_review(
    source_directory: str | Path, output_directory: str | Path
) -> dict[str, Any]:
    source = Path(source_directory)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = [
        {"event_type": "review_started", "status": "ok"}
    ]
    loaded, missing, invalid_json = _load_review_inputs(source)
    artifact_hashes = review_artifact_hashes(source)
    for artifact_name, record in artifact_hashes.items():
        if record["present"]:
            events.append(
                {
                    "event_type": "review_artifact_hash_computed",
                    "status": "ok",
                    "artifact_name": artifact_name,
                }
            )
    candidate = loaded.get("recovery_profile_candidate.json", {})
    shadow_observations = loaded.get("shadow_observations.json", {})
    shadow_quality = loaded.get("shadow_quality_report.json", {})
    gate_results, warnings, blocking, matrix = evaluate_review_gates(
        candidate if isinstance(candidate, dict) else {},
        shadow_quality if isinstance(shadow_quality, dict) else {},
        shadow_observations if isinstance(shadow_observations, dict) else {},
    )
    warnings = _deterministic_review_warnings(
        warnings,
        shadow_quality if isinstance(shadow_quality, dict) else {},
        shadow_observations if isinstance(shadow_observations, dict) else {},
        optional_validation_present=artifact_hashes["shadow_validation_report.json"]["present"],
    )
    blocking = sorted(
        dict.fromkeys(
            [f"missing_review_artifact:{name}" for name in missing]
            + [f"invalid_review_json:{name}" for name in invalid_json]
            + blocking
        )
    )
    if missing or invalid_json:
        status = "candidate_invalid"
        confidence = "blocked_or_invalid"
        passed = False
    elif blocking:
        status = "candidate_blocked"
        confidence = "blocked_or_invalid"
        passed = False
    elif warnings:
        status = "candidate_reviewable_with_warnings"
        confidence = "reviewable_with_warnings"
        passed = True
    else:
        status = "candidate_reviewable"
        confidence = "reviewable"
        passed = True
    profile_id = (
        candidate.get("profile_id")
        if isinstance(candidate, dict) and isinstance(candidate.get("profile_id"), str)
        else "unknown"
    )
    package = _review_package(
        profile_id=profile_id,
        candidate=candidate if isinstance(candidate, dict) else {},
        shadow_quality=shadow_quality if isinstance(shadow_quality, dict) else {},
        status=status,
        confidence=confidence,
        gate_results=gate_results,
        warnings=warnings,
        blocking=blocking,
        artifact_hashes=artifact_hashes,
    )
    report = _review_report(
        profile_id=profile_id,
        status=status,
        passed=passed,
        warnings=warnings,
        blocking=blocking,
        matrix=matrix,
        artifact_hashes=artifact_hashes,
    )
    for gate in gate_results:
        events.append(gate_event(gate["gate_id"], gate["gate_status"], gate["reasons"]))
    events.append({"event_type": "candidate_review_package_built", "status": "ok" if passed else "blocked"})
    events.append({"event_type": "review_decision_template_written", "status": "ok"})
    events.append(
        {
            "event_type": "review_completed",
            "status": "ok" if passed else "blocked",
            "candidate_review_status": status,
        }
    )
    write_json(output / "review_schema.json", review_schema_document())
    write_json(output / "candidate_review_package.json", package)
    write_json(output / "candidate_review_report.json", report)
    write_json(output / "review_decision_template.json", review_decision_template(profile_id))
    write_review_trace(output / "review_trace.jsonl", events)
    return report


def _load_review_inputs(root: Path) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    loaded: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    invalid: list[str] = []
    for name in REVIEW_REQUIRED_FILES:
        path = root / name
        if not path.is_file():
            missing.append(name)
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid.append(name)
            continue
        if not isinstance(payload, dict):
            invalid.append(name)
            continue
        loaded[name] = payload
    optional = root / "shadow_validation_report.json"
    if optional.is_file():
        try:
            payload = json.loads(optional.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                loaded["shadow_validation_report.json"] = payload
        except (OSError, json.JSONDecodeError):
            invalid.append("shadow_validation_report.json")
    return loaded, missing, invalid


def _review_package(
    *,
    profile_id: str,
    candidate: dict[str, Any],
    shadow_quality: dict[str, Any],
    status: str,
    confidence: str,
    gate_results: list[dict[str, Any]],
    warnings: list[str],
    blocking: list[str],
    artifact_hashes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    tiles = candidate.get("tiles", [])
    assigned = candidate.get("assigned_workloads", [])
    field_coverage = shadow_quality.get("field_coverage", {})
    overall = (
        field_coverage.get("overall_field_coverage", 0.0)
        if isinstance(field_coverage, dict)
        else 0.0
    )
    conflict_matrix = shadow_quality.get("conflict_matrix", {})
    return {
        **review_read_only_fields(),
        "profile_id": profile_id,
        "candidate_profile_loaded": bool(candidate),
        "shadow_quality_loaded": bool(shadow_quality),
        "candidate_review_status": status,
        "candidate_review_confidence": confidence,
        "candidate_summary": {
            "profile_candidate": candidate.get("profile_candidate") is True,
            "human_review_required": candidate.get("human_review_required") is True,
            "hardware_execution_enabled": candidate.get("hardware_execution_enabled") is True,
            "runtime_loader_hint": candidate.get("runtime_loader_hint"),
            "voltage_policy": candidate.get("voltage_policy"),
            "tile_count": len(tiles) if isinstance(tiles, list) else 0,
            "assigned_workloads_count": len(assigned) if isinstance(assigned, list) else 0,
        },
        "shadow_quality_summary": {
            "shadow_quality_score": shadow_quality.get("shadow_quality_score", 0.0),
            "shadow_quality_band": shadow_quality.get("shadow_quality_band", "insufficient"),
            "conflict_count": conflict_matrix.get("conflict_count", 0)
            if isinstance(conflict_matrix, dict)
            else 0,
            "field_coverage_overall": overall,
        },
        "candidate_profile_snapshot": candidate,
        "review_gate_results": gate_results,
        "review_artifact_hashes": artifact_hashes,
        "review_warnings": sorted(dict.fromkeys(warnings)),
        "review_blocking_reasons": sorted(dict.fromkeys(blocking)),
        "known_limitations": [
            "review_package_only",
            "requires_explicit_review_decision",
            "not_certification",
            "not_hardware_control",
            "dry_run_only",
        ],
    }


def _review_report(
    *,
    profile_id: str,
    status: str,
    passed: bool,
    warnings: list[str],
    blocking: list[str],
    matrix: dict[str, Any],
    artifact_hashes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        **review_read_only_fields(),
        "profile_id": profile_id,
        "candidate_review_status": status,
        "candidate_review_passed": passed,
        "candidate_review_blocked": not passed,
        "candidate_review_stage": "completed" if passed else "blocked",
        "candidate_review_reasons": ["candidate_review_package_built"] if passed else [],
        "candidate_review_warnings": sorted(dict.fromkeys(warnings)),
        "candidate_review_blocking_reasons": sorted(dict.fromkeys(blocking)),
        "review_gate_matrix": matrix,
        "review_artifact_hashes": artifact_hashes,
        "promotion_allowed": False,
        "promotion_requires_review_decision": True,
        "known_limitations": [
            "candidate_review_is_not_promotion",
            "not_certification",
            "not_hardware_control",
            "dry_run_only",
        ],
    }


def _deterministic_review_warnings(
    raw_warnings: list[str],
    shadow_quality: dict[str, Any],
    shadow_observations: dict[str, Any],
    *,
    optional_validation_present: bool,
) -> list[str]:
    warnings: list[str] = []
    if raw_warnings:
        warnings.append("candidate_review_has_warnings")
    band = shadow_quality.get("shadow_quality_band")
    if band == "low":
        warnings.append("shadow_quality_low")
    elif band == "medium":
        warnings.append("shadow_quality_medium")
    for payload in (shadow_quality, shadow_observations):
        matrix = payload.get("conflict_matrix")
        if isinstance(matrix, dict) and matrix.get("conflict_count", 0):
            warnings.append("candidate_conflicts_require_review")
            break
    if not optional_validation_present:
        warnings.append("optional_shadow_validation_report_missing")
    return sorted(dict.fromkeys(warnings))
