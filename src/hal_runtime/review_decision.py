"""Review decision template and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .review_integrity import file_hash_record
from .review_models import (
    REQUIRED_ACKNOWLEDGEMENTS,
    REVIEW_DECISION_MATRIX_KEYS,
    review_boundary_fields,
)
from .shadow_validator import unsafe_shadow_fields


def review_decision_template(profile_id: str) -> dict[str, Any]:
    return {
        **review_boundary_fields(),
        "review_decision_template": True,
        "profile_id": profile_id,
        "reviewer_id": None,
        "review_timestamp": None,
        "human_review_approved": False,
        "approved_for": "dry_run_only",
        "acknowledged_limitations": {
            name: False for name in REQUIRED_ACKNOWLEDGEMENTS
        },
        "review_notes": "",
        "required_acknowledgements": list(REQUIRED_ACKNOWLEDGEMENTS),
    }


def load_review_decision(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("review_decision_root_must_be_object")
    return payload


def load_review_decision_with_provenance(
    path: str | Path | None,
) -> tuple[dict[str, Any] | None, dict[str, Any], str | None]:
    provenance = empty_review_decision_provenance()
    if path is None:
        return None, provenance, "missing_review_decision"
    artifact = Path(path)
    record = file_hash_record(artifact)
    if not record["present"]:
        return None, provenance, "missing_review_decision"
    provenance.update(
        {
            "review_decision_loaded": True,
            "review_decision_sha256": record["sha256"],
            "review_decision_size_bytes": record["size_bytes"],
        }
    )
    try:
        decision = load_review_decision(artifact)
    except (OSError, ValueError, json.JSONDecodeError):
        return None, provenance, "invalid_review_decision_json"
    valid, _blocking, summary = validate_review_decision(decision)
    provenance.update(summary)
    provenance["decision_source"] = "explicit_review_decision_file"
    return decision, provenance, None if valid else "invalid_review_decision"


def empty_review_decision_provenance() -> dict[str, Any]:
    return {
        "review_decision_loaded": False,
        "review_decision_sha256": None,
        "review_decision_size_bytes": None,
        "reviewer_id_present": False,
        "review_timestamp_present": False,
        "approved_for": None,
        "human_review_approved": False,
        "all_required_acknowledgements_true": False,
        "decision_source": None,
    }


def validate_review_decision(decision: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    blocking: list[str] = []
    if decision.get("simulation_only") is not True:
        blocking.append("review_decision_simulation_only_not_true")
    if decision.get("hardware_control_enabled") is not False:
        blocking.append("review_decision_hardware_control_enabled_true")
    if decision.get("claim_boundary") != "simulation_only_not_certified":
        blocking.append("review_decision_claim_boundary_not_simulation_only_not_certified")
    if decision.get("real_execution_allowed") is True:
        blocking.append("review_decision_real_execution_allowed_true")
    if decision.get("certification_passed") is True:
        blocking.append("review_decision_certification_passed_true")
    for field in unsafe_shadow_fields(decision):
        reason = f"review_decision_safety_boundary_violation:{field}_true"
        if field not in {"hardware_control_enabled", "real_execution_allowed", "certification_passed"}:
            blocking.append(reason)
    if decision.get("human_review_approved") is not True:
        blocking.append("review_decision_human_review_approved_false")
    if decision.get("approved_for") != "dry_run_only":
        blocking.append("review_decision_approved_for_not_dry_run_only")
    reviewer = decision.get("reviewer_id")
    if not isinstance(reviewer, str) or not reviewer.strip():
        blocking.append("review_decision_reviewer_id_missing")
    timestamp = decision.get("review_timestamp")
    if not isinstance(timestamp, str) or not timestamp.strip():
        blocking.append("review_decision_review_timestamp_missing")
    acknowledgements = decision.get("acknowledged_limitations")
    if not isinstance(acknowledgements, dict):
        acknowledgements = {}
    for name in REQUIRED_ACKNOWLEDGEMENTS:
        if acknowledgements.get(name) is not True:
            blocking.append(f"review_decision_acknowledgement_missing:{name}")
    summary = {
        "human_review_approved": decision.get("human_review_approved") is True,
        "approved_for": decision.get("approved_for"),
        "reviewer_id_present": isinstance(reviewer, str) and bool(reviewer.strip()),
        "review_timestamp_present": isinstance(timestamp, str) and bool(timestamp.strip()),
        "all_required_acknowledgements_true": all(
            acknowledgements.get(name) is True for name in REQUIRED_ACKNOWLEDGEMENTS
        ),
        "decision_source": "explicit_review_decision_file",
    }
    return not blocking, sorted(dict.fromkeys(blocking)), summary


def review_decision_validation_matrix(
    decision: dict[str, Any] | None,
    *,
    decision_present: bool,
    json_valid: bool,
    candidate_review_passed: bool,
    candidate_safety_passed: bool,
    decision_blocking: list[str] | None = None,
    candidate_blocking: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    decision_blocking = sorted(dict.fromkeys(decision_blocking or []))
    candidate_blocking = sorted(dict.fromkeys(candidate_blocking or []))

    def entry(passed: bool, reasons: list[str], *, evaluated: bool = True) -> dict[str, Any]:
        return {
            "passed": passed,
            "status": "ok" if passed else "blocked" if evaluated else "not_evaluated",
            "reasons": sorted(dict.fromkeys(reasons)),
        }

    not_evaluated = not decision_present or not json_valid or decision is None
    matrix = {
        "decision_file_present": entry(decision_present, [] if decision_present else ["review_decision_missing"]),
        "json_validity": entry(
            json_valid,
            [] if json_valid else (["review_decision_invalid_json"] if decision_present else []),
            evaluated=decision_present,
        ),
        "approval_scope": entry(
            bool(decision and decision.get("approved_for") == "dry_run_only"),
            [r for r in decision_blocking if r == "review_decision_approved_for_not_dry_run_only"],
            evaluated=not not_evaluated,
        ),
        "human_approval": entry(
            bool(decision and decision.get("human_review_approved") is True),
            [r for r in decision_blocking if r == "review_decision_human_review_approved_false"],
            evaluated=not not_evaluated,
        ),
        "reviewer_identity": entry(
            bool(decision and isinstance(decision.get("reviewer_id"), str) and decision["reviewer_id"].strip()),
            [r for r in decision_blocking if r == "review_decision_reviewer_id_missing"],
            evaluated=not not_evaluated,
        ),
        "review_timestamp": entry(
            bool(decision and isinstance(decision.get("review_timestamp"), str) and decision["review_timestamp"].strip()),
            [r for r in decision_blocking if r == "review_decision_review_timestamp_missing"],
            evaluated=not not_evaluated,
        ),
        "required_acknowledgements": entry(
            bool(decision) and not any("acknowledgement_missing:" in r for r in decision_blocking),
            [r for r in decision_blocking if "acknowledgement_missing:" in r],
            evaluated=not not_evaluated,
        ),
        "decision_safety_boundary": entry(
            bool(decision) and not any(
                token in r
                for r in decision_blocking
                for token in ("safety_boundary", "hardware_control_enabled", "real_execution_allowed", "certification_passed", "simulation_only_not_true", "claim_boundary")
            ),
            [
                r for r in decision_blocking
                if any(token in r for token in ("safety_boundary", "hardware_control_enabled", "real_execution_allowed", "certification_passed", "simulation_only_not_true", "claim_boundary"))
            ],
            evaluated=not not_evaluated,
        ),
        "candidate_review_status": entry(
            candidate_review_passed,
            [] if candidate_review_passed else ["candidate_review_package_blocked"],
        ),
        "candidate_safety_invariants": entry(
            candidate_safety_passed,
            candidate_blocking,
        ),
    }
    return {key: matrix[key] for key in REVIEW_DECISION_MATRIX_KEYS}
