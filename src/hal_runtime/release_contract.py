"""Stable public PoC contract for HAL Recovery Runtime v1.0.0."""

from __future__ import annotations

from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION


PUBLIC_POC_CONTRACT_VERSION = RUNTIME_VERSION

SUPPORTED_CLI_COMMANDS = (
    "validate-profile",
    "check-compat",
    "plan",
    "dry-run",
    "validate-bundle",
    "dry-run-bundle",
    "list-adapters",
    "simulate-plan",
    "list-failure-modes",
    "simulate-failure",
    "list-policies",
    "simulate-policy",
    "list-evidence-schema",
    "build-evidence-bundle",
    "validate-evidence-bundle",
    "list-pipeline-stages",
    "run-pipeline",
    "list-shadow-schemas",
    "ingest-shadow-data",
    "validate-shadow-data",
    "list-review-gates",
    "build-candidate-review",
    "validate-candidate-review",
    "promote-reviewed-profile",
    "show-release-contract",
    "validate-public-poc",
)

SUPPORTED_ARTIFACTS = (
    "runtime_plan.json",
    "runtime_report.json",
    "runtime_events.jsonl",
    "bundle_validation_report.json",
    "adapter_registry.json",
    "adapter_report.json",
    "adapter_trace.jsonl",
    "failure_modes.json",
    "rollback_plan.json",
    "rollback_report.json",
    "failure_trace.jsonl",
    "policy_modes.json",
    "policy_decision.json",
    "policy_report.json",
    "policy_trace.jsonl",
    "evidence_schema.json",
    "evidence_manifest.json",
    "evidence_bundle.json",
    "evidence_report.json",
    "evidence_validation_report.json",
    "pipeline_stages.json",
    "pipeline_summary.json",
    "pipeline_report.json",
    "pipeline_artifact_index.json",
    "pipeline_trace.jsonl",
    "shadow_schema.json",
    "shadow_observations.json",
    "shadow_ingestion_report.json",
    "shadow_validation_report.json",
    "recovery_profile_candidate.json",
    "shadow_quality_report.json",
    "review_schema.json",
    "candidate_review_package.json",
    "candidate_review_report.json",
    "candidate_review_validation_report.json",
    "review_decision_template.json",
    "reviewed_recovery_profile.json",
    "profile_promotion_report.json",
    "review_trace.jsonl",
    "release_contract.json",
    "public_poc_report.json",
    "public_poc_validation_report.json",
    "public_poc_trace.jsonl",
)

SUPPORTED_WORKFLOW = (
    "shadow_ingestion",
    "shadow_validation",
    "candidate_review",
    "explicit_review_decision",
    "dry_run_profile_promotion",
    "runtime_dry_run",
    "optional_simulation_pipeline",
    "evidence_validation",
)

UNSUPPORTED_CAPABILITIES = (
    "hardware_control",
    "real_execution",
    "real_recovery",
    "real_" + "rollback",
    "real_policy_" + "enforcement",
    "ate_" + "control",
    "wafer_prober_" + "control",
    "instrument_" + "control",
    "certification",
    "production_approval",
)


def release_contract_document() -> dict[str, Any]:
    """Return the deterministic, path-free v1.0.0 public PoC contract."""
    return {
        "runtime_version": RUNTIME_VERSION,
        "public_poc_contract_version": PUBLIC_POC_CONTRACT_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "release_status": "public_poc",
        "stability_level": "stable_poc_contract",
        "supported_workflow": list(SUPPORTED_WORKFLOW),
        "supported_cli_commands": list(SUPPORTED_CLI_COMMANDS),
        "supported_artifacts": list(SUPPORTED_ARTIFACTS),
        "required_safety_invariants": {
            "simulation_only": True,
            "hardware_control_enabled": False,
            "hardware_execution_enabled": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "review_approval_scope": "dry_run_only",
        },
        "unsupported_capabilities": list(UNSUPPORTED_CAPABILITIES),
        "exit_code_contract": {
            "0": "valid_or_completed_simulation_only_operation",
            "2": "invalid_blocked_or_safety_boundary_operation",
            "1": "unexpected_internal_failure_if_used",
        },
        "schema_version_mapping": {
            "runtime": RUNTIME_VERSION,
            "review_gate": RUNTIME_VERSION,
            "review_semantics": RUNTIME_VERSION,
            "shadow_ingestion": RUNTIME_VERSION,
            "shadow_quality_semantics": RUNTIME_VERSION,
            "pipeline_runner": RUNTIME_VERSION,
            "pipeline_report_semantics": RUNTIME_VERSION,
            "evidence_bundle": RUNTIME_VERSION,
            "evidence_validation_semantics": RUNTIME_VERSION,
        },
        "known_limitations": [
            "public_proof_of_concept",
            "local_files_only",
            "manual_review_required",
            "dry_run_only",
            "not_certified",
            "no_hardware_control",
        ],
    }
