"""Validate source artifacts and built simulation-only evidence bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .evidence_hasher import sha256_file
from .evidence_models import (
    EvidenceBundleValidationOutcome,
    EvidenceCheck,
    EvidenceCollection,
)
from .evidence_schema import (
    EVIDENCE_BUNDLE_VERSION,
    EVIDENCE_VALIDATION_PRIORITY_ORDER,
    EVIDENCE_VALIDATION_SEMANTICS_VERSION,
    FAILURE_CATEGORIES,
    VALIDATION_STAGES,
    build_validation_matrix,
    expected_optional_artifacts,
)
from .models import RUNTIME_VERSION


JSON_ARTIFACT_SUFFIX = ".json"
BAD_SELECTED_POLICY_PARTS = (
    "hardware_" + "execute",
    "real_execute",
    "apply_to_" + "device",
    "firmware_update",
    "voltage_adjust",
    "timing_adjust",
    "driver_apply",
)


def validate_collected_evidence(collection: EvidenceCollection) -> EvidenceCheck:
    parsed: dict[str, dict[str, Any]] = {}
    warnings = list(collection.warnings)
    invalid_required_json: list[str] = []
    for artifact in collection.artifacts:
        if not artifact.artifact_name.endswith(JSON_ARTIFACT_SUFFIX):
            continue
        try:
            payload = json.loads(artifact.source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            if artifact.required:
                invalid_required_json.append(artifact.artifact_name)
            else:
                warnings.append(
                    f"optional_artifact_invalid_json:{artifact.artifact_name}"
                )
            continue
        if not isinstance(payload, dict):
            if artifact.required:
                invalid_required_json.append(artifact.artifact_name)
            else:
                warnings.append(
                    f"optional_artifact_invalid_json:{artifact.artifact_name}"
                )
            continue
        parsed[artifact.artifact_name] = payload
        if "runtime_version" in payload and payload.get("runtime_version") != RUNTIME_VERSION:
            warnings.append(f"version_mismatch:{artifact.artifact_name}")

    violations = _source_safety_violations(parsed)
    profile_entries = _profile_id_entries(parsed)
    profile_ids = set(profile_entries.values())
    profile_id = next(iter(profile_ids), None)
    policy_mismatch = _policy_mismatch(parsed)
    runtime_inconsistency = _runtime_policy_inconsistency(parsed)
    missing_optional = expected_optional_artifacts(
        {artifact.artifact_name for artifact in collection.artifacts}
    )
    warnings.extend(f"missing_optional_artifact:{name}" for name in missing_optional)

    missing_reasons = [
        f"missing_required_artifact:{name}"
        for name in collection.missing_required_artifacts
    ]
    json_reasons = [f"invalid_json:{name}" for name in invalid_required_json]
    safety_reasons = [
        f"safety_boundary_violation:{reason}" for reason in violations
    ]
    profile_reasons = _profile_mismatch_reasons(profile_entries)
    policy_reasons = (
        ["policy_decision_mismatch:selected_policy"] if policy_mismatch else []
    )
    runtime_policy_reasons = (
        ["policy_runtime_inconsistency:blocked_plan_allowed"]
        if runtime_inconsistency
        else []
    )
    failures = {
        "required_artifacts": missing_reasons,
        "json_validity": json_reasons,
        "hash_integrity": [],
        "manifest_integrity": [],
        "copied_artifacts": [],
        "safety_boundary": safety_reasons,
        "profile_consistency": profile_reasons,
        "policy_consistency": policy_reasons,
        "runtime_policy_consistency": runtime_policy_reasons,
    }

    if safety_reasons:
        status = "blocked_safety_boundary"
    elif json_reasons:
        status = "invalid_artifact_json"
    elif missing_reasons:
        status = "invalid_missing_required_artifacts"
    elif profile_reasons:
        status = "invalid_profile_id_mismatch"
    elif policy_mismatch:
        status = "invalid_policy_decision_mismatch"
    elif runtime_inconsistency:
        status = "invalid_policy_runtime_inconsistency"
    elif warnings:
        status = "valid_with_warnings"
    else:
        status = "valid_evidence_bundle"
    passed = status in {"valid_evidence_bundle", "valid_with_warnings"}
    status_reasons = {
        "blocked_safety_boundary": safety_reasons,
        "invalid_artifact_json": json_reasons,
        "invalid_missing_required_artifacts": missing_reasons,
        "invalid_profile_id_mismatch": profile_reasons,
        "invalid_policy_decision_mismatch": policy_reasons,
        "invalid_policy_runtime_inconsistency": runtime_policy_reasons,
        "valid_with_warnings": ["evidence_bundle_valid_with_warnings"],
        "valid_evidence_bundle": ["evidence_bundle_valid"],
    }
    validation_reasons = tuple(status_reasons[status])
    reasons = validation_reasons
    matrix = build_validation_matrix(failures, warnings)
    return EvidenceCheck(
        validation_passed=passed,
        validation_status=status,
        profile_id=profile_id,
        parsed_artifacts=parsed,
        missing_optional_artifacts=missing_optional,
        safety_boundary_violations=tuple(dict.fromkeys(violations)),
        consistency_warnings=tuple(dict.fromkeys(warnings)),
        evidence_reasons=reasons,
        evidence_validation_reasons=validation_reasons,
        evidence_warning_reasons=tuple(dict.fromkeys(warnings)),
        evidence_failure_category=FAILURE_CATEGORIES[status],
        evidence_validation_stage=VALIDATION_STAGES[status],
        evidence_validation_matrix=matrix,
    )


def validate_built_evidence(
    bundle_directory: str | Path,
) -> EvidenceBundleValidationOutcome:
    root = Path(bundle_directory)
    required_bundle_files = (
        "evidence_manifest.json",
        "evidence_bundle.json",
        "evidence_report.json",
    )
    loaded: dict[str, dict[str, Any]] = {}
    invalid_files: list[str] = []
    for name in required_bundle_files:
        path = root / name
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid_files.append(name)
            continue
        if not isinstance(payload, dict):
            invalid_files.append(name)
            continue
        loaded[name] = payload

    mismatches: list[str] = []
    missing_manifest_entries: list[str] = []
    missing_copied_artifacts: list[str] = []
    violations: list[str] = []
    warnings: list[str] = []
    manifest = loaded.get("evidence_manifest.json", {})
    copied = root / "artifacts"
    entries = manifest.get("artifacts")
    entry_map: dict[str, dict[str, Any]] = {}
    if isinstance(entries, list):
        entry_map = {
            str(entry.get("artifact_name")): entry
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get("artifact_name"), str)
        }
    else:
        missing_manifest_entries.append("evidence_manifest.json.artifacts")
    if copied.is_dir():
        for path in sorted(copied.iterdir(), key=lambda item: item.name):
            if path.is_file() and path.name not in entry_map:
                missing_manifest_entries.append(path.name)
    for name, entry in entry_map.items():
        path = copied / name
        if not path.is_file():
            missing_copied_artifacts.append(name)
            continue
        expected_hash = entry.get("sha256")
        expected_size = entry.get("size_bytes")
        if (
            not isinstance(expected_hash, str)
            or sha256_file(path) != expected_hash
            or not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or path.stat().st_size != expected_size
        ):
            mismatches.append(name)

    for name, payload in loaded.items():
        if payload.get("simulation_only") is not True:
            violations.append(f"{name}.simulation_only")
        if payload.get("hardware_control_enabled") is not False:
            violations.append(f"{name}.hardware_control_enabled")
        if payload.get("claim_boundary") != CLAIM_BOUNDARY:
            violations.append(f"{name}.claim_boundary")
        if "runtime_version" in payload and payload.get("runtime_version") != RUNTIME_VERSION:
            warnings.append(f"version_mismatch:{name}")
        if payload.get("evidence_bundle_version") != EVIDENCE_BUNDLE_VERSION:
            warnings.append(f"evidence_version_mismatch:{name}")
    for name in ("evidence_manifest.json", "evidence_bundle.json"):
        if not isinstance(loaded.get(name, {}).get("bundle_id"), str):
            missing_manifest_entries.append(f"{name}.bundle_id")
    if isinstance(entries, list) and manifest.get("artifact_count") != len(entries):
        missing_manifest_entries.append("evidence_manifest.json.artifact_count")
    bundle = loaded.get("evidence_bundle.json", {})
    safety_summary = bundle.get("safety_summary")
    if isinstance(safety_summary, dict):
        for field in (
            "hardware_control_enabled_anywhere",
            "real_execution_allowed_anywhere",
            "policy_allows_hardware_control",
        ):
            if safety_summary.get(field) is not False:
                violations.append(f"evidence_bundle.json.safety_summary.{field}")
        if safety_summary.get("claim_boundary_consistent") is not True:
            violations.append(
                "evidence_bundle.json.safety_summary.claim_boundary_consistent"
            )
    else:
        violations.append("evidence_bundle.json.safety_summary")
    report = loaded.get("evidence_report.json", {})
    report_warnings = report.get("evidence_warning_reasons")
    if not isinstance(report_warnings, list):
        report_warnings = report.get("consistency_warnings", [])
    warnings.extend(item for item in report_warnings if isinstance(item, str))

    original_status = report.get("evidence_validation_status")
    original_reasons = report.get("evidence_validation_reasons", [])
    if not isinstance(original_reasons, list):
        original_reasons = []
    source_status_reasons = [
        reason for reason in original_reasons if isinstance(reason, str)
    ]
    json_reasons = [f"invalid_json:{name}" for name in invalid_files]
    required_reasons: list[str] = []
    profile_reasons: list[str] = []
    policy_reasons: list[str] = []
    runtime_policy_reasons: list[str] = []
    if original_status == "invalid_artifact_json":
        json_reasons.extend(source_status_reasons)
    elif original_status == "invalid_missing_required_artifacts":
        required_reasons.extend(source_status_reasons)
    elif original_status == "invalid_profile_id_mismatch":
        profile_reasons.extend(source_status_reasons)
    elif original_status == "invalid_policy_decision_mismatch":
        policy_reasons.extend(source_status_reasons)
    elif original_status == "invalid_policy_runtime_inconsistency":
        runtime_policy_reasons.extend(source_status_reasons)
    if original_status == "blocked_safety_boundary":
        violations.extend(
            reason.split(":", 1)[1]
            for reason in source_status_reasons
            if reason.startswith("safety_boundary_violation:")
        )

    safety_reasons = [
        f"safety_boundary_violation:{reason}"
        for reason in dict.fromkeys(violations)
    ]
    manifest_reasons = [
        f"missing_manifest_entry:{name}"
        for name in dict.fromkeys(missing_manifest_entries)
    ]
    copied_reasons = [
        f"missing_copied_artifact:{name}"
        for name in dict.fromkeys(missing_copied_artifacts)
    ]
    hash_reasons = [
        f"hash_mismatch:{name}" for name in dict.fromkeys(mismatches)
    ]
    failures = {
        "required_artifacts": required_reasons,
        "json_validity": list(dict.fromkeys(json_reasons)),
        "hash_integrity": hash_reasons,
        "manifest_integrity": manifest_reasons,
        "copied_artifacts": copied_reasons,
        "safety_boundary": safety_reasons,
        "profile_consistency": profile_reasons,
        "policy_consistency": policy_reasons,
        "runtime_policy_consistency": runtime_policy_reasons,
    }
    status_by_matrix = (
        ("blocked_safety_boundary", "safety_boundary"),
        ("invalid_artifact_json", "json_validity"),
        ("invalid_missing_required_artifacts", "required_artifacts"),
        ("invalid_missing_manifest_entries", "manifest_integrity"),
        ("invalid_missing_copied_artifacts", "copied_artifacts"),
        ("invalid_hash_mismatch", "hash_integrity"),
        ("invalid_profile_id_mismatch", "profile_consistency"),
        ("invalid_policy_decision_mismatch", "policy_consistency"),
        ("invalid_policy_runtime_inconsistency", "runtime_policy_consistency"),
    )
    status = next(
        (candidate for candidate, key in status_by_matrix if failures[key]),
        "valid_with_warnings" if warnings else "valid_evidence_bundle",
    )
    if status == "valid_evidence_bundle":
        validation_reasons = ["evidence_bundle_valid"]
    elif status == "valid_with_warnings":
        validation_reasons = ["evidence_bundle_valid_with_warnings"]
    else:
        matrix_key = next(key for candidate, key in status_by_matrix if candidate == status)
        validation_reasons = failures[matrix_key]
    passed = status in {"valid_evidence_bundle", "valid_with_warnings"}
    warning_reasons = list(dict.fromkeys(warnings))
    matrix = build_validation_matrix(failures, warning_reasons)
    hashes_verified = bool(entry_map) and not (
        mismatches or missing_manifest_entries or missing_copied_artifacts
    )
    trace_events = _validation_trace_events(
        invalid_files=invalid_files,
        mismatches=mismatches,
        missing_manifest_entries=missing_manifest_entries,
        missing_copied_artifacts=missing_copied_artifacts,
        violations=violations,
        warnings=warning_reasons,
        status=status,
    )
    return EvidenceBundleValidationOutcome(
        {
            "runtime_version": RUNTIME_VERSION,
            "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
            "evidence_validation_semantics_version": EVIDENCE_VALIDATION_SEMANTICS_VERSION,
            "simulation_only": True,
            "hardware_control_enabled": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "evidence_bundle_loaded": len(loaded) == len(required_bundle_files),
            "evidence_validation_passed": passed,
            "evidence_validation_status": status,
            "evidence_failure_category": FAILURE_CATEGORIES[status],
            "evidence_validation_stage": VALIDATION_STAGES[status],
            "evidence_validation_reasons": validation_reasons,
            "evidence_warning_reasons": warning_reasons,
            "evidence_validation_priority_order": list(
                EVIDENCE_VALIDATION_PRIORITY_ORDER
            ),
            "evidence_validation_matrix": matrix,
            "hashes_verified": hashes_verified,
            "hash_mismatches": list(dict.fromkeys(mismatches)),
            "missing_manifest_entries": list(
                dict.fromkeys(missing_manifest_entries)
            ),
            "missing_copied_artifacts": list(
                dict.fromkeys(missing_copied_artifacts)
            ),
            "safety_boundary_violations": list(dict.fromkeys(violations)),
            "consistency_warnings": warning_reasons,
            "known_limitations": [
                "hash_verification_only",
                "not_certification",
                "no_hardware_control",
            ],
        },
        trace_events,
    )


def _source_safety_violations(
    parsed: dict[str, dict[str, Any]],
) -> list[str]:
    violations: list[str] = []
    for name, payload in parsed.items():
        if "claim_boundary" in payload and payload["claim_boundary"] != CLAIM_BOUNDARY:
            violations.append(f"{name}.claim_boundary")
        if "hardware_control_enabled" in payload and payload["hardware_control_enabled"] is not False:
            violations.append(f"{name}.hardware_control_enabled")
    for name in ("policy_report.json", "policy_decision.json"):
        payload = parsed.get(name)
        if not payload:
            continue
        for field in (
            "real_execution_allowed",
            "hardware_control_allowed",
            "retry_allowed",
        ):
            if payload.get(field) is not False:
                violations.append(f"{name}.{field}_true")
        selected = payload.get("selected_policy")
        if not isinstance(selected, str) or any(
            forbidden in selected for forbidden in BAD_SELECTED_POLICY_PARTS
        ):
            violations.append(f"{name}.selected_policy")
    return violations


def _validation_trace_events(
    *,
    invalid_files: list[str],
    mismatches: list[str],
    missing_manifest_entries: list[str],
    missing_copied_artifacts: list[str],
    violations: list[str],
    warnings: list[str],
    status: str,
) -> tuple[dict[str, Any], ...]:
    events: list[dict[str, Any]] = [
        {"event_type": "evidence_validation_started", "status": "ok"}
    ]
    for name in dict.fromkeys(invalid_files):
        events.append(
            {
                "event_type": "evidence_artifact_json_invalid",
                "status": "invalid",
                "artifact_name": name,
            }
        )
    for name in dict.fromkeys(missing_manifest_entries):
        events.append(
            {
                "event_type": "evidence_manifest_entry_missing",
                "status": "invalid",
                "artifact_name": name,
            }
        )
    for name in dict.fromkeys(missing_copied_artifacts):
        events.append(
            {
                "event_type": "evidence_copied_artifact_missing",
                "status": "invalid",
                "artifact_name": name,
            }
        )
    for name in dict.fromkeys(mismatches):
        events.append(
            {
                "event_type": "evidence_hash_mismatch_detected",
                "status": "invalid",
                "artifact_name": name,
            }
        )
    for reason in dict.fromkeys(violations):
        events.append(
            {
                "event_type": "evidence_safety_boundary_violation",
                "status": "blocked",
                "reason": reason,
            }
        )
    for reason in warnings:
        events.append(
            {
                "event_type": "evidence_warning_detected",
                "status": "warning",
                "reason": reason,
            }
        )
    if status in {"valid_evidence_bundle", "valid_with_warnings"}:
        events.append(
            {"event_type": "evidence_validation_completed", "status": status}
        )
    else:
        events.append(
            {"event_type": "evidence_validation_failed", "status": status}
        )
    return tuple(events)


def _profile_id_entries(parsed: dict[str, dict[str, Any]]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name, payload in parsed.items():
        candidates: list[Any] = [payload.get("profile_id")]
        source_summary = payload.get("source_plan_summary")
        if isinstance(source_summary, dict):
            candidates.append(source_summary.get("profile_id"))
        for candidate in candidates:
            if isinstance(candidate, str) and candidate:
                values[name] = candidate
                break
    return values


def _profile_mismatch_reasons(entries: dict[str, str]) -> list[str]:
    if len(set(entries.values())) <= 1:
        return []
    baseline = entries.get("runtime_plan.json") or next(iter(entries.values()))
    return [
        f"profile_id_mismatch:{name}"
        for name, profile_id in sorted(entries.items())
        if profile_id != baseline
    ]


def _policy_mismatch(parsed: dict[str, dict[str, Any]]) -> bool:
    report = parsed.get("policy_report.json")
    decision = parsed.get("policy_decision.json")
    return bool(
        report
        and decision
        and report.get("selected_policy") != decision.get("selected_policy")
    )


def _runtime_policy_inconsistency(parsed: dict[str, dict[str, Any]]) -> bool:
    plan = parsed.get("runtime_plan.json")
    decision = parsed.get("policy_decision.json")
    if not plan or not decision:
        return False
    status = plan.get("plan_status")
    selected = decision.get("selected_policy")
    return bool(
        isinstance(status, str)
        and status.startswith("blocked_")
        and selected in {"dry_run_allowed", "dry_run_allowed_with_warnings"}
    )
