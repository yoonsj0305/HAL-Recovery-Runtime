"""Load and validate immutable simulation-only policy configuration."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .policy_models import PolicyConfig, PolicyConfigValidation
from .policy_rules import supported_policy_modes


REQUIRED_POLICY_FIELDS = (
    "policy_config_id",
    "policy_mode",
    "human_review_required",
    "allow_retry",
    "allow_real_execution",
    "allow_hardware_control",
    "simulation_only",
    "hardware_control_enabled",
    "claim_boundary",
)


class PolicyConfigLoadError(ValueError):
    """Raised when a policy configuration cannot be decoded as an object."""


def default_policy_config() -> PolicyConfig:
    return PolicyConfig(
        policy_config_id="POLICY_DEFAULT_SIMULATION_ONLY",
        policy_mode="conservative_default",
        human_review_required=True,
        allow_retry=False,
        allow_real_execution=False,
        allow_hardware_control=False,
        simulation_only=True,
        hardware_control_enabled=False,
        claim_boundary=CLAIM_BOUNDARY,
    )


def load_policy_config(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise PolicyConfigLoadError("policy_config_not_readable") from exc
    except json.JSONDecodeError as exc:
        raise PolicyConfigLoadError("policy_config_invalid_json") from exc
    if not isinstance(payload, dict):
        raise PolicyConfigLoadError("policy_config_not_object")
    return payload


def validate_policy_config(config: Mapping[str, Any]) -> PolicyConfigValidation:
    structural = [
        f"missing_required_field:{field}"
        for field in REQUIRED_POLICY_FIELDS
        if field not in config
    ]
    for field in ("policy_config_id", "policy_mode", "claim_boundary"):
        if field in config and not isinstance(config[field], str):
            structural.append(f"{field}_must_be_string")
    for field in (
        "human_review_required",
        "allow_retry",
        "allow_real_execution",
        "allow_hardware_control",
        "simulation_only",
        "hardware_control_enabled",
    ):
        if field in config and not isinstance(config[field], bool):
            structural.append(f"{field}_must_be_boolean")
    for field in ("max_allowed_blocked_actions", "max_allowed_degraded_flags"):
        if field in config and (
            not isinstance(config[field], int)
            or isinstance(config[field], bool)
            or config[field] < 0
        ):
            structural.append(f"{field}_must_be_nonnegative_integer")
    if "notes" in config and not isinstance(config["notes"], str):
        structural.append("notes_must_be_string")
    mode = config.get("policy_mode")
    if isinstance(mode, str) and mode not in supported_policy_modes():
        structural.append(f"unsupported_policy_mode:{mode}")

    safety: list[str] = []
    if config.get("simulation_only") is not True:
        safety.append("simulation_only_must_be_true")
    if config.get("hardware_control_enabled") is not False:
        safety.append("hardware_control_enabled_must_be_false")
    if config.get("claim_boundary") != CLAIM_BOUNDARY:
        safety.append("claim_boundary_must_be_simulation_only_not_certified")
    if config.get("allow_real_execution") is not False:
        safety.append("allow_real_execution_must_be_false")
    if config.get("allow_hardware_control") is not False:
        safety.append("allow_hardware_control_must_be_false")
    if config.get("allow_retry") is not False:
        safety.append("allow_retry_must_be_false")
    return PolicyConfigValidation(not structural, not structural and not safety, tuple(structural), tuple(safety))


def policy_config_from_mapping(config: Mapping[str, Any]) -> PolicyConfig:
    return PolicyConfig(
        policy_config_id=str(config["policy_config_id"]),
        policy_mode=str(config["policy_mode"]),
        human_review_required=bool(config["human_review_required"]),
        allow_retry=bool(config["allow_retry"]),
        allow_real_execution=bool(config["allow_real_execution"]),
        allow_hardware_control=bool(config["allow_hardware_control"]),
        simulation_only=bool(config["simulation_only"]),
        hardware_control_enabled=bool(config["hardware_control_enabled"]),
        claim_boundary=str(config["claim_boundary"]),
        max_allowed_blocked_actions=int(config.get("max_allowed_blocked_actions", 0)),
        max_allowed_degraded_flags=int(config.get("max_allowed_degraded_flags", 0)),
        notes=config.get("notes") if isinstance(config.get("notes"), str) else None,
    )
