"""Models and validation for simulation-only failure scenarios."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CLAIM_BOUNDARY = "simulation_only_not_certified"


@dataclass(frozen=True)
class FailureScenario:
    scenario_id: str
    failure_mode: str
    injection_stage: str
    simulation_only: bool
    hardware_control_enabled: bool
    claim_boundary: str
    target_action_id: str | None = None
    target_adapter_id: str | None = None
    target_workload_id: str | None = None
    notes: str | None = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "failure_mode": self.failure_mode,
            "injection_stage": self.injection_stage,
            "target_action_id": self.target_action_id,
            "target_adapter_id": self.target_adapter_id,
        }


@dataclass(frozen=True)
class ScenarioValidationResult:
    valid: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class FailureInjectionResult:
    simulated_action_ids: tuple[str, ...]
    failed_action_ids: tuple[str, ...]
    skipped_action_ids: tuple[str, ...]
    failure_reasons: tuple[str, ...]
    rollback_strategy: str
    injected_failure_action_id: str | None
    action_outcomes: tuple[tuple[str, str], ...]


class ScenarioLoadError(ValueError):
    pass


def default_failure_scenario() -> FailureScenario:
    return FailureScenario(
        scenario_id="SCN_NONE",
        failure_mode="none",
        injection_stage="adapter_simulation",
        simulation_only=True,
        hardware_control_enabled=False,
        claim_boundary=CLAIM_BOUNDARY,
    )


def load_failure_scenario(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScenarioLoadError("scenario_not_readable") from exc
    except json.JSONDecodeError as exc:
        raise ScenarioLoadError("scenario_invalid_json") from exc
    if not isinstance(value, dict):
        raise ScenarioLoadError("scenario_not_object")
    return value


def validate_failure_scenario(
    value: Mapping[str, Any], supported_modes: set[str]
) -> ScenarioValidationResult:
    required = (
        "scenario_id",
        "failure_mode",
        "injection_stage",
        "simulation_only",
        "hardware_control_enabled",
        "claim_boundary",
    )
    reasons = [f"missing_required_field:{field}" for field in required if field not in value]
    mode = value.get("failure_mode")
    if "failure_mode" in value and mode not in supported_modes:
        reasons.append(f"unsupported_failure_mode:{mode}")
    if "simulation_only" in value and value["simulation_only"] is not True:
        reasons.append("simulation_only_must_be_true")
    if "hardware_control_enabled" in value and value["hardware_control_enabled"] is not False:
        reasons.append("hardware_control_enabled_must_be_false")
    if "claim_boundary" in value and value["claim_boundary"] != CLAIM_BOUNDARY:
        reasons.append("claim_boundary_must_be_simulation_only_not_certified")
    return ScenarioValidationResult(not reasons, tuple(reasons))


def scenario_from_mapping(value: Mapping[str, Any]) -> FailureScenario:
    def optional_string(field: str) -> str | None:
        item = value.get(field)
        return item if isinstance(item, str) else None

    return FailureScenario(
        scenario_id=str(value["scenario_id"]),
        failure_mode=str(value["failure_mode"]),
        injection_stage=str(value["injection_stage"]),
        simulation_only=value["simulation_only"] is True,
        hardware_control_enabled=value["hardware_control_enabled"] is True,
        claim_boundary=str(value["claim_boundary"]),
        target_action_id=optional_string("target_action_id"),
        target_adapter_id=optional_string("target_adapter_id"),
        target_workload_id=optional_string("target_workload_id"),
        notes=optional_string("notes"),
    )

