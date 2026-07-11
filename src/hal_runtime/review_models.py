"""Shared models and constants for candidate review gates."""

from __future__ import annotations

from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION


REVIEW_GATE_VERSION = RUNTIME_VERSION
REVIEW_SEMANTICS_VERSION = RUNTIME_VERSION
REQUIRED_ACKNOWLEDGEMENTS = (
    "not_hardware_control",
    "not_certification",
    "candidate_quality_reviewed",
    "conflicts_reviewed",
    "dry_run_only",
)
REVIEW_GATE_IDS = (
    "candidate_schema_gate",
    "candidate_safety_gate",
    "shadow_quality_gate",
    "conflict_review_gate",
    "human_review_decision_gate",
)
REVIEW_REQUIRED_FILES = (
    "recovery_profile_candidate.json",
    "shadow_observations.json",
    "shadow_quality_report.json",
    "shadow_ingestion_report.json",
)
REVIEW_OPTIONAL_FILES = ("shadow_validation_report.json",)
REVIEW_HASHED_FILES = REVIEW_REQUIRED_FILES + REVIEW_OPTIONAL_FILES
REVIEW_DECISION_MATRIX_KEYS = (
    "decision_file_present",
    "json_validity",
    "approval_scope",
    "human_approval",
    "reviewer_identity",
    "review_timestamp",
    "required_acknowledgements",
    "decision_safety_boundary",
    "candidate_review_status",
    "candidate_safety_invariants",
)


def review_boundary_fields() -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "review_gate_version": REVIEW_GATE_VERSION,
        "review_semantics_version": REVIEW_SEMANTICS_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def review_read_only_fields() -> dict[str, Any]:
    return {
        **review_boundary_fields(),
        "read_only": True,
        "review_required": True,
    }
