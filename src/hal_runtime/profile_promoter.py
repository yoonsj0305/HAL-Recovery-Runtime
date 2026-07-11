"""Promote reviewed candidates into dry-run-only Runtime profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .event_log import write_json
from .review_decision import (
    empty_review_decision_provenance,
    load_review_decision_with_provenance,
    review_decision_validation_matrix,
    validate_review_decision,
)
from .review_gate import candidate_safety_reasons
from .review_integrity import file_hash_record
from .review_models import REQUIRED_ACKNOWLEDGEMENTS, review_boundary_fields
from .review_semantics import review_failure_category, review_validation_stage
from .review_trace import write_review_trace
from .shadow_schema import ALLOWED_CANDIDATE_ROLES


def promote_reviewed_profile(
    review_directory: str | Path,
    review_decision_path: str | Path,
    output_directory: str | Path,
) -> dict[str, Any]:
    root = Path(review_directory)
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = [{"event_type": "promotion_started", "status": "ok"}]

    package, report, load_reasons = _load_package(root)
    candidate = package.get("candidate_profile_snapshot", {})
    if not isinstance(candidate, dict):
        candidate = {}
    candidate_reasons = candidate_safety_reasons(candidate)
    candidate_review_passed = (
        not load_reasons
        and report.get("candidate_review_passed") is True
        and package.get("candidate_review_status") not in {"candidate_blocked", "candidate_invalid"}
    )
    if not candidate_review_passed and not load_reasons:
        load_reasons.append("candidate_review_package_blocked")
    integrity_reasons = _artifact_integrity_reasons(package, report)

    decision, provenance, decision_error = load_review_decision_with_provenance(
        review_decision_path
    )
    decision_blocking: list[str] = []
    if decision_error == "missing_review_decision":
        decision_blocking = ["review_decision_missing"]
    elif decision_error == "invalid_review_decision_json":
        decision_blocking = ["review_decision_invalid_json"]
    elif decision is not None:
        _decision_valid, decision_blocking, _summary = validate_review_decision(decision)

    decision_present = provenance["review_decision_loaded"] is True
    json_valid = decision_present and decision is not None
    matrix = review_decision_validation_matrix(
        decision,
        decision_present=decision_present,
        json_valid=json_valid,
        candidate_review_passed=candidate_review_passed,
        candidate_safety_passed=not candidate_reasons,
        decision_blocking=decision_blocking,
        candidate_blocking=candidate_reasons,
    )
    blocking = sorted(
        dict.fromkeys(load_reasons + integrity_reasons + decision_blocking + candidate_reasons)
    )
    lineage = _promotion_lineage(root, package, provenance)
    preflight = _promotion_preflight(
        package,
        candidate_review_passed=candidate_review_passed,
        decision_valid=decision is not None and not decision_blocking,
        candidate_safety_passed=not candidate_reasons,
        provenance=provenance,
    )
    if blocking or not preflight["promotion_preflight_passed"]:
        blocking = sorted(dict.fromkeys(blocking + ["promotion_preflight_failed"]))

    profile_id = (
        package.get("profile_id")
        if isinstance(package.get("profile_id"), str)
        else candidate.get("profile_id", "unknown")
        if isinstance(candidate, dict)
        else "unknown"
    )
    warnings = _promotion_warnings(package)
    passed = not blocking and preflight["promotion_preflight_passed"]
    category = review_failure_category(
        blocking,
        decision_error=decision_error,
        warnings_only=bool(warnings and not blocking),
    )
    stage = (
        "completed"
        if passed
        else review_validation_stage(
            blocking,
            decision_error=decision_error,
            promotion=True,
        )
    )
    promotion_report = _promotion_report(
        profile_id=profile_id,
        passed=passed,
        provenance=provenance,
        matrix=matrix,
        category=category,
        stage=stage,
        preflight=preflight,
        lineage=lineage,
        warnings=warnings,
        blocking=blocking,
    )

    events.extend(_decision_events(provenance, blocking))
    events.append(
        {
            "event_type": "promotion_preflight_checked",
            "status": "ok" if passed else "blocked",
        }
    )
    if passed and decision is not None:
        reviewed = _reviewed_profile(profile_id, decision, lineage)
        write_json(output / "reviewed_recovery_profile.json", reviewed)
        events.append({"event_type": "promotion_artifact_lineage_built", "status": "ok"})
        events.append({"event_type": "reviewed_profile_written", "status": "ok"})
        events.append(
            {
                "event_type": "promotion_completed",
                "status": "ok",
                "promotion_status": "profile_promoted_for_dry_run",
            }
        )
    else:
        for reason in decision_blocking:
            events.append(
                {"event_type": "review_decision_blocked", "status": "blocked", "reason": reason}
            )
        events.append(
            {"event_type": "promotion_blocked", "status": "blocked", "reasons": blocking}
        )
    write_json(output / "profile_promotion_report.json", promotion_report)
    write_review_trace(output / "review_trace.jsonl", events)
    return promotion_report


def _load_package(root: Path) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    reasons: list[str] = []
    loaded: dict[str, dict[str, Any]] = {}
    for name in ("candidate_review_package.json", "candidate_review_report.json"):
        path = root / name
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            reasons.append(f"missing_or_invalid_review_artifact:{name}")
            continue
        if not isinstance(payload, dict):
            reasons.append(f"invalid_review_artifact:{name}")
            continue
        loaded[name] = payload
    return (
        loaded.get("candidate_review_package.json", {}),
        loaded.get("candidate_review_report.json", {}),
        reasons,
    )


def _artifact_integrity_reasons(
    package: dict[str, Any], report: dict[str, Any]
) -> list[str]:
    package_hashes = package.get("review_artifact_hashes")
    report_hashes = report.get("review_artifact_hashes")
    if not isinstance(package_hashes, dict) or not isinstance(report_hashes, dict):
        return ["artifact_hash_mismatch:review_artifact_hashes"]
    return [
        f"artifact_hash_mismatch:{name}"
        for name in sorted(set(package_hashes) | set(report_hashes))
        if package_hashes.get(name) != report_hashes.get(name)
    ]


def _promotion_preflight(
    package: dict[str, Any],
    *,
    candidate_review_passed: bool,
    decision_valid: bool,
    candidate_safety_passed: bool,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    hashes = package.get("review_artifact_hashes", {})
    required_names = (
        "recovery_profile_candidate.json",
        "shadow_observations.json",
        "shadow_quality_report.json",
        "shadow_ingestion_report.json",
    )
    hashes_recorded = isinstance(hashes, dict) and all(
        isinstance(hashes.get(name), dict)
        and hashes[name].get("present") is True
        and isinstance(hashes[name].get("sha256"), str)
        for name in required_names
    )
    approved = provenance.get("approved_for") == "dry_run_only"
    checks = {
        "candidate_review_passed": candidate_review_passed,
        "review_decision_valid": decision_valid,
        "candidate_safety_invariants_passed": candidate_safety_passed,
        "artifact_hashes_recorded": hashes_recorded,
        "review_decision_hash_recorded": isinstance(provenance.get("review_decision_sha256"), str),
        "approved_for_dry_run_only": approved,
        "promotion_scope": "dry_run_only",
    }
    checks["promotion_preflight_passed"] = all(
        value is True for key, value in checks.items() if key != "promotion_scope"
    )
    return checks


def _promotion_lineage(
    root: Path,
    package: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    hashes = package.get("review_artifact_hashes", {})
    candidate_record = hashes.get("recovery_profile_candidate.json", {}) if isinstance(hashes, dict) else {}
    boundary = review_boundary_fields()
    return {
        "origin_type": "shadow_candidate_review",
        "candidate_profile_sha256": candidate_record.get("sha256") if isinstance(candidate_record, dict) else None,
        "candidate_review_package_sha256": file_hash_record(root / "candidate_review_package.json")["sha256"],
        "candidate_review_report_sha256": file_hash_record(root / "candidate_review_report.json")["sha256"],
        "review_decision_sha256": provenance.get("review_decision_sha256"),
        "review_gate_version": boundary["review_gate_version"],
        "review_semantics_version": boundary["review_semantics_version"],
        "promotion_scope": "dry_run_only",
    }


def _reviewed_profile(
    profile_id: str,
    decision: dict[str, Any],
    lineage: dict[str, Any],
) -> dict[str, Any]:
    boundary = review_boundary_fields()
    return {
        **boundary,
        "profile_id": profile_id,
        "human_review_required": True,
        "human_review_completed": True,
        "hardware_execution_enabled": False,
        "runtime_loader_hint": "simulation_only",
        "voltage_policy": "no_hardware_control",
        "tiles": [],
        "assigned_workloads": [],
        "unassigned_workloads": [],
        "preferred_routes": [],
        "blocked_roles": [],
        "allowed_roles": list(ALLOWED_CANDIDATE_ROLES),
        "review_metadata": {
            "reviewer_id": decision.get("reviewer_id"),
            "review_timestamp": decision.get("review_timestamp"),
            "approved_for": "dry_run_only",
            "acknowledged_limitations": {
                name: True for name in REQUIRED_ACKNOWLEDGEMENTS
            },
        },
        "profile_origin": {
            "origin_type": "shadow_candidate_review",
            "candidate_profile_id": profile_id,
            "review_gate_version": boundary["review_gate_version"],
            "review_semantics_version": boundary["review_semantics_version"],
            "promotion_scope": "dry_run_only",
            "lineage_hashes_present": all(
                isinstance(lineage.get(name), str)
                for name in (
                    "candidate_profile_sha256",
                    "candidate_review_package_sha256",
                    "candidate_review_report_sha256",
                    "review_decision_sha256",
                )
            ),
        },
        "profile_promotion_lineage": lineage,
        "known_limitations": [
            "reviewed_for_dry_run_only",
            "not_hardware_control",
            "not_certification",
            "not_safe_for_direct_hardware_application",
        ],
    }


def _promotion_report(
    *,
    profile_id: str,
    passed: bool,
    provenance: dict[str, Any],
    matrix: dict[str, Any],
    category: str,
    stage: str,
    preflight: dict[str, Any],
    lineage: dict[str, Any],
    warnings: list[str],
    blocking: list[str],
) -> dict[str, Any]:
    return {
        **review_boundary_fields(),
        "profile_id": profile_id,
        "promotion_status": "profile_promoted_for_dry_run" if passed else "promotion_blocked",
        "promotion_passed": passed,
        "promotion_blocked": not passed,
        "promotion_stage": "completed" if passed else "blocked",
        "review_validation_stage": stage,
        "review_failure_category": category,
        "promotion_reasons": [
            "explicit_human_review_decision_approved",
            "all_required_acknowledgements_present",
            "candidate_safety_invariants_passed",
            "dry_run_only_profile_written",
        ] if passed else [],
        "promotion_warning_reasons": warnings,
        "promotion_blocking_reasons": sorted(dict.fromkeys(blocking)),
        "review_decision_summary": {
            "human_review_approved": provenance["human_review_approved"],
            "approved_for": provenance["approved_for"],
            "reviewer_id_present": provenance["reviewer_id_present"],
            "review_timestamp_present": provenance["review_timestamp_present"],
            "all_acknowledgements_true": provenance["all_required_acknowledgements_true"],
        },
        "review_decision_provenance": provenance,
        "review_decision_validation_matrix": matrix,
        "promotion_preflight_summary": preflight,
        "profile_promotion_lineage": lineage,
        "known_limitations": [
            "promotion_is_dry_run_only",
            "lineage_proves_continuity_not_hardware_safety",
            "not_certification",
            "not_hardware_control",
            "not_production_approval",
        ],
    }


def _promotion_warnings(package: dict[str, Any]) -> list[str]:
    values = package.get("review_warnings", [])
    return sorted(str(value) for value in values) if isinstance(values, list) else []


def _decision_events(
    provenance: dict[str, Any], blocking: list[str]
) -> list[dict[str, Any]]:
    events = [
        {
            "event_type": "review_decision_loaded",
            "status": "ok" if provenance["review_decision_loaded"] else "blocked",
        }
    ]
    if provenance["review_decision_sha256"]:
        events.append({"event_type": "review_decision_hash_computed", "status": "ok"})
    events.append({"event_type": "review_decision_validation_matrix_built", "status": "ok"})
    if not blocking:
        events.append(
            {"event_type": "review_decision_validated", "status": "ok", "promotion_would_be_allowed": True}
        )
    return events
