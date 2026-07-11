"""Construct bounded evidence manifest, bundle, and report payloads."""

from __future__ import annotations

from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .evidence_models import EvidenceCheck, EvidenceCollection
from .evidence_schema import (
    EVIDENCE_BUNDLE_VERSION,
    EVIDENCE_VALIDATION_PRIORITY_ORDER,
    EVIDENCE_VALIDATION_SEMANTICS_VERSION,
)
from .models import RUNTIME_VERSION


BUNDLE_ID = "EVIDENCE_BUNDLE_001"


def build_manifest(collection: EvidenceCollection) -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "evidence_validation_semantics_version": EVIDENCE_VALIDATION_SEMANTICS_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "bundle_id": BUNDLE_ID,
        "source_directory": collection.source_directory.name,
        "artifact_count": len(collection.artifacts),
        "artifacts": [artifact.to_dict() for artifact in collection.artifacts],
        "missing_artifacts": list(collection.missing_required_artifacts),
        "unsupported_artifacts": list(collection.unsupported_artifacts),
        "known_limitations": [
            "simulation_only",
            "not_certified",
            "no_hardware_control",
            "evidence_hashes_do_not_certify_real_execution",
        ],
    }


def build_bundle(
    collection: EvidenceCollection, check: EvidenceCheck
) -> dict[str, Any]:
    parsed = check.parsed_artifacts
    names = {artifact.artifact_name for artifact in collection.artifacts}
    runtime = parsed.get("runtime_report.json", {})
    adapter = parsed.get("adapter_report.json", {})
    rollback = parsed.get("rollback_report.json", {})
    policy = parsed.get("policy_report.json", {})
    anywhere_hardware = any(
        payload.get("hardware_control_enabled") is True
        for payload in parsed.values()
    )
    anywhere_real = any(
        payload.get("real_execution_allowed") is True for payload in parsed.values()
    )
    policy_hardware = any(
        parsed.get(name, {}).get("hardware_control_allowed") is True
        for name in ("policy_report.json", "policy_decision.json")
    )
    claim_consistent = not any(
        violation.endswith(".claim_boundary")
        for violation in check.safety_boundary_violations
    )
    if check.validation_status == "valid_evidence_bundle":
        evidence_status = "evidence_bundle_built"
        confidence = "simulation_only_audit_trail"
    elif check.validation_status == "valid_with_warnings":
        evidence_status = "evidence_bundle_built_with_warnings"
        confidence = "simulation_only_with_warnings"
    elif check.validation_status == "blocked_safety_boundary":
        evidence_status = "evidence_bundle_blocked"
        confidence = "blocked_or_invalid"
    else:
        evidence_status = "evidence_bundle_invalid"
        confidence = "blocked_or_invalid"
    return {
        "runtime_version": RUNTIME_VERSION,
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "bundle_id": BUNDLE_ID,
        "profile_id": check.profile_id,
        "evidence_status": evidence_status,
        "evidence_confidence": confidence,
        "artifact_summary": {
            "runtime_plan_present": "runtime_plan.json" in names,
            "runtime_report_present": "runtime_report.json" in names,
            "adapter_report_present": "adapter_report.json" in names,
            "rollback_report_present": "rollback_report.json" in names,
            "policy_report_present": "policy_report.json" in names,
        },
        "safety_summary": {
            "hardware_control_enabled_anywhere": anywhere_hardware,
            "real_execution_allowed_anywhere": anywhere_real,
            "policy_allows_hardware_control": policy_hardware,
            "claim_boundary_consistent": claim_consistent,
        },
        "decision_summary": {
            "runtime_status": runtime.get("runtime_status"),
            "adapter_simulation_status": adapter.get("adapter_simulation_status"),
            "rollback_simulation_status": rollback.get("rollback_simulation_status"),
            "selected_policy": policy.get("selected_policy"),
            "policy_status": policy.get("policy_status"),
        },
        "trace_summary": {
            "runtime_events_present": "runtime_events.jsonl" in names,
            "adapter_trace_present": "adapter_trace.jsonl" in names,
            "failure_trace_present": "failure_trace.jsonl" in names,
            "policy_trace_present": "policy_trace.jsonl" in names,
        },
        "artifact_hashes": {
            artifact.artifact_name: artifact.sha256
            for artifact in collection.artifacts
        },
        "known_limitations": [
            "simulation_only",
            "not_certified",
            "no_real_hardware_validation",
            "no_" + "real_policy_" + "enforcement",
        ],
    }


def build_report(
    collection: EvidenceCollection,
    check: EvidenceCheck,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "evidence_bundle_version": EVIDENCE_BUNDLE_VERSION,
        "evidence_validation_semantics_version": EVIDENCE_VALIDATION_SEMANTICS_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "bundle_loaded": True,
        "manifest_built": True,
        "evidence_validation_passed": check.validation_passed,
        "evidence_status": bundle["evidence_status"],
        "evidence_validation_status": check.validation_status,
        "evidence_failure_category": check.evidence_failure_category,
        "evidence_validation_stage": check.evidence_validation_stage,
        "evidence_validation_reasons": list(check.evidence_validation_reasons),
        "evidence_warning_reasons": list(check.evidence_warning_reasons),
        "evidence_validation_priority_order": list(
            EVIDENCE_VALIDATION_PRIORITY_ORDER
        ),
        "evidence_validation_matrix": check.evidence_validation_matrix,
        "profile_id": check.profile_id,
        "artifact_count": len(collection.artifacts),
        "required_artifacts_present": not collection.missing_required_artifacts,
        "missing_required_artifacts": list(collection.missing_required_artifacts),
        "missing_optional_artifacts": list(check.missing_optional_artifacts),
        "hashes_computed": bool(collection.artifacts),
        "hash_algorithm": "sha256",
        "safety_boundary_violations": list(check.safety_boundary_violations),
        "consistency_warnings": list(check.consistency_warnings),
        "evidence_reasons": list(check.evidence_reasons),
        "known_limitations": [
            "simulation_only",
            "not_certified",
            "hash_integrity_only_not_certification",
            "no_hardware_control",
        ],
    }
