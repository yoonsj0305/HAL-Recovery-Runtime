"""Validate candidate review packages and optional explicit review decisions."""

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
from .review_models import review_boundary_fields
from .review_semantics import review_failure_category, review_validation_stage
from .review_trace import write_review_trace


REVIEW_ARTIFACTS = (
    "candidate_review_package.json",
    "candidate_review_report.json",
    "review_decision_template.json",
)


def validate_candidate_review(
    review_directory: str | Path,
    output_directory: str | Path,
    review_decision_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(review_directory)
    loaded, missing, invalid_json = _load_review_artifacts(root)
    package = loaded.get("candidate_review_package.json", {})
    report = loaded.get("candidate_review_report.json", {})
    candidate = package.get("candidate_profile_snapshot", {})
    if not isinstance(candidate, dict):
        candidate = {}

    package_blocking = sorted(
        dict.fromkeys(
            [f"missing_review_artifact:{name}" for name in missing]
            + [f"invalid_review_json:{name}" for name in invalid_json]
            + _boundary_reasons(loaded)
            + _artifact_integrity_reasons(package, report)
        )
    )
    candidate_review_passed = (
        not package_blocking
        and report.get("candidate_review_passed") is True
        and package.get("candidate_review_status") not in {"candidate_blocked", "candidate_invalid"}
    )
    if not candidate_review_passed and not package_blocking:
        package_blocking.append("candidate_review_package_blocked")
    candidate_blocking = candidate_safety_reasons(candidate)

    decision: dict[str, Any] | None = None
    provenance = empty_review_decision_provenance()
    decision_error: str | None = None
    decision_blocking: list[str] = []
    if review_decision_path is not None:
        decision, provenance, decision_error = load_review_decision_with_provenance(
            review_decision_path
        )
        if decision_error == "missing_review_decision":
            decision_blocking = ["review_decision_missing"]
        elif decision_error == "invalid_review_decision_json":
            decision_blocking = ["review_decision_invalid_json"]
        elif decision is not None:
            _valid, decision_blocking, _summary = validate_review_decision(decision)

    blocking = sorted(
        dict.fromkeys(package_blocking + candidate_blocking + decision_blocking)
    )
    decision_present = provenance["review_decision_loaded"] is True
    json_valid = decision_present and decision is not None
    matrix = review_decision_validation_matrix(
        decision,
        decision_present=decision_present,
        json_valid=json_valid,
        candidate_review_passed=candidate_review_passed,
        candidate_safety_passed=not candidate_blocking,
        decision_blocking=decision_blocking,
        candidate_blocking=candidate_blocking,
    )
    decision_valid = review_decision_path is not None and decision is not None and not decision_blocking
    promotion_would_be_allowed = bool(
        decision_valid and candidate_review_passed and not candidate_blocking and not package_blocking
    )
    warnings = _review_warnings(package)
    if review_decision_path is None:
        warnings.append("review_decision_not_loaded_promotion_pending")

    if review_decision_path is None and candidate_review_passed and not candidate_blocking:
        status = "valid_candidate_review"
        passed = True
        reasons = ["candidate_review_package_valid"]
    elif promotion_would_be_allowed:
        status = "promotion_decision_valid"
        passed = True
        reasons = ["promotion_decision_valid"]
    else:
        status = "promotion_decision_blocked" if review_decision_path is not None else "invalid_candidate_review_artifacts"
        passed = False
        reasons = blocking

    category = review_failure_category(
        blocking,
        decision_error=decision_error,
        decision_missing_pending=review_decision_path is None,
        warnings_only=bool(warnings and not blocking),
    )
    stage = (
        "completed"
        if passed or review_decision_path is None
        else review_validation_stage(blocking, decision_error=decision_error)
    )
    validation = {
        **review_boundary_fields(),
        "candidate_review_loaded": not missing and not invalid_json,
        "candidate_review_validation_passed": passed,
        "candidate_review_validation_status": status,
        "promotion_would_be_allowed": promotion_would_be_allowed,
        "review_decision_loaded": provenance["review_decision_loaded"],
        "review_decision_provenance": provenance,
        "review_decision_validation_matrix": matrix,
        "review_failure_category": category,
        "review_validation_stage": stage,
        "validation_reasons": sorted(dict.fromkeys(reasons)),
        "warning_reasons": sorted(dict.fromkeys(warnings)),
        "blocking_reasons": blocking,
        "known_limitations": [
            "validation_only",
            "not_promotion",
            "not_hardware_control",
            "not_certification",
        ],
    }
    output = Path(output_directory)
    write_json(output / "candidate_review_validation_report.json", validation)
    write_review_trace(output / "review_trace.jsonl", _validation_events(
        review_decision_path is not None,
        provenance,
        matrix,
        promotion_would_be_allowed,
        blocking,
    ))
    return validation


def _load_review_artifacts(root: Path) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    loaded: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    invalid: list[str] = []
    for name in REVIEW_ARTIFACTS:
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
    return loaded, missing, invalid


def _boundary_reasons(loaded: dict[str, dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for name, payload in loaded.items():
        if payload.get("simulation_only") is not True:
            reasons.append(f"{name}.simulation_only")
        if payload.get("hardware_control_enabled") is not False:
            reasons.append(f"{name}.hardware_control_enabled")
        if payload.get("claim_boundary") != "simulation_only_not_certified":
            reasons.append(f"{name}.claim_boundary")
    return reasons


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


def _review_warnings(package: dict[str, Any]) -> list[str]:
    values = package.get("review_warnings", [])
    return sorted(str(value) for value in values) if isinstance(values, list) else []


def _validation_events(
    decision_requested: bool,
    provenance: dict[str, Any],
    matrix: dict[str, Any],
    promotion_would_be_allowed: bool,
    blocking: list[str],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if decision_requested:
        events.append(
            {
                "event_type": "review_decision_loaded",
                "status": "ok" if provenance["review_decision_loaded"] else "blocked",
            }
        )
        if provenance["review_decision_sha256"]:
            events.append({"event_type": "review_decision_hash_computed", "status": "ok"})
    events.append({"event_type": "review_decision_validation_matrix_built", "status": "ok"})
    if promotion_would_be_allowed:
        events.append(
            {
                "event_type": "review_decision_validated",
                "status": "ok",
                "promotion_would_be_allowed": True,
            }
        )
    elif decision_requested:
        for reason in sorted(blocking):
            if reason.startswith("review_decision_"):
                events.append(
                    {"event_type": "review_decision_blocked", "status": "blocked", "reason": reason}
                )
    return events
