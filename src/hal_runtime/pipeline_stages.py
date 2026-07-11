"""Fixed stage registry for the simulation-only pipeline runner."""

from __future__ import annotations

from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION


PIPELINE_RUNNER_VERSION = RUNTIME_VERSION
PIPELINE_STAGE_NAMES = (
    "input_load",
    "runtime_dry_run",
    "adapter_simulation",
    "failure_rollback_simulation",
    "policy_simulation",
    "evidence_bundle",
    "pipeline_report",
)
KNOWN_PIPELINE_LIMITATIONS = (
    "simulation_only",
    "not_certified",
    "no_hardware_control",
    "no_" + "real_policy_" + "enforcement",
)
PIPELINE_DEPENDENCY_GRAPH = {
    "input_load": (),
    "runtime_dry_run": ("input_load",),
    "adapter_simulation": ("runtime_dry_run",),
    "failure_rollback_simulation": ("runtime_dry_run", "adapter_simulation"),
    "policy_simulation": (
        "runtime_dry_run",
        "adapter_simulation",
        "failure_rollback_simulation",
    ),
    "evidence_bundle": ("runtime_dry_run", "policy_simulation"),
    "pipeline_report": (),
}


def pipeline_stages_document() -> dict[str, Any]:
    """Return the stable v1.0.0 stage registry."""

    return {
        "runtime_version": RUNTIME_VERSION,
        "pipeline_runner_version": PIPELINE_RUNNER_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "stages": [
            {
                "stage_id": "stage_01_input_load",
                "stage_name": "input_load",
                "required": True,
                "description": "Load recovery profile or compiler bundle.",
            },
            {
                "stage_id": "stage_02_runtime_dry_run",
                "stage_name": "runtime_dry_run",
                "required": True,
                "description": "Build runtime plan and runtime report without hardware control.",
            },
            {
                "stage_id": "stage_03_adapter_simulation",
                "stage_name": "adapter_simulation",
                "required": True,
                "description": "Simulate runtime plan through mock adapters.",
            },
            {
                "stage_id": "stage_04_failure_rollback_simulation",
                "stage_name": "failure_rollback_simulation",
                "required": True,
                "description": "Run failure injection and rollback simulation.",
            },
            {
                "stage_id": "stage_05_policy_simulation",
                "stage_name": "policy_simulation",
                "required": True,
                "description": "Select simulation-only runtime policy.",
            },
            {
                "stage_id": "stage_06_evidence_bundle",
                "stage_name": "evidence_bundle",
                "required": False,
                "description": "Build end-to-end evidence bundle.",
            },
            {
                "stage_id": "stage_07_pipeline_report",
                "stage_name": "pipeline_report",
                "required": True,
                "description": "Summarize pipeline status and artifacts.",
            },
        ],
        "known_limitations": list(KNOWN_PIPELINE_LIMITATIONS),
    }
