"""Fixed schema metadata for the candidate-to-profile review gate."""

from __future__ import annotations

from typing import Any

from .review_models import review_read_only_fields


REVIEW_GATES = (
    {
        "gate_id": "candidate_schema_gate",
        "required": True,
        "description": "Candidate profile must have required simulation-only fields.",
    },
    {
        "gate_id": "candidate_safety_gate",
        "required": True,
        "description": "Candidate must not allow hardware execution or hardware control.",
    },
    {
        "gate_id": "shadow_quality_gate",
        "required": True,
        "description": "Shadow quality must be sufficient for dry-run review.",
    },
    {
        "gate_id": "conflict_review_gate",
        "required": True,
        "description": "Conflicting observations must be surfaced for human review.",
    },
    {
        "gate_id": "human_review_decision_gate",
        "required": True,
        "description": "Promotion requires explicit review_decision.json.",
    },
)


def review_schema_document() -> dict[str, Any]:
    return {
        **review_read_only_fields(),
        "review_gates": [dict(gate) for gate in REVIEW_GATES],
        "known_limitations": [
            "simulation_only",
            "not_certification",
            "not_hardware_control",
            "reviewed_profile_is_for_dry_run_only",
        ],
    }
