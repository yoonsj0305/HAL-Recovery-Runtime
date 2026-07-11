"""Orchestrate input validation and simulation-only policy selection."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .adapter_simulator import PlanLoadError, load_runtime_plan, validate_runtime_plan
from .event_log import write_json
from .policy_audit import (
    build_decision_path,
    build_rule_results,
    build_warning_inputs,
    first_matched_rule,
)
from .policy_config import (
    PolicyConfigLoadError,
    default_policy_config,
    load_policy_config,
    policy_config_from_mapping,
    validate_policy_config,
)
from .policy_evaluator import evaluate_policy
from .policy_models import PolicyConfig, PolicyDecision, PolicySimulationOutcome
from .policy_report import build_policy_report
from .policy_trace import write_policy_trace


class PolicyArtifactLoadError(ValueError):
    """Raised when an optional policy input artifact is invalid."""


def simulate_policy_file(
    plan_path: str | Path,
    output_dir: str | Path,
    adapter_report_path: str | Path | None = None,
    rollback_report_path: str | Path | None = None,
    policy_config_path: str | Path | None = None,
) -> PolicySimulationOutcome:
    config = default_policy_config()
    config_present = policy_config_path is not None
    config_loaded = not config_present
    try:
        plan = load_runtime_plan(plan_path)
    except PlanLoadError as exc:
        return _write_blocked(
            None, config, output_dir, "no_action_taken", "invalid_policy_input",
            (str(exc),), matched_rule="invalid_input", plan_loaded=False,
            config_loaded=config_loaded, config_present=config_present,
        )

    validation = validate_runtime_plan(plan)
    if not validation.structurally_valid:
        return _write_blocked(
            plan, config, output_dir, "no_action_taken", "invalid_policy_input",
            validation.validation_reasons, matched_rule="invalid_input",
            config_loaded=config_loaded, config_present=config_present,
        )

    config_status = "default"
    config_safety_reasons: tuple[str, ...] = ()
    if config_present:
        config_status = "ok"
        try:
            raw_config = load_policy_config(policy_config_path)
        except PolicyConfigLoadError as exc:
            return _write_blocked(
                plan, config, output_dir, "blocked_invalid_artifacts",
                "blocked_invalid_artifacts", (str(exc),),
                matched_rule="invalid_input", config_loaded=False,
                config_present=True, input_scope="policy_config",
            )
        config_validation = validate_policy_config(raw_config)
        config_loaded = True
        if not config_validation.structurally_valid:
            return _write_blocked(
                plan, config, output_dir, "blocked_invalid_artifacts",
                "blocked_invalid_artifacts", config_validation.structural_reasons,
                matched_rule="invalid_input", config_loaded=True,
                config_present=True, input_scope="policy_config",
            )
        config = policy_config_from_mapping(raw_config)
        if not config_validation.safety_boundary_passed:
            config_safety_reasons = config_validation.safety_reasons

    adapter_report, adapter_loaded, adapter_error = _load_optional_report(
        adapter_report_path, "adapter"
    )
    rollback_report, rollback_loaded, rollback_error = _load_optional_report(
        rollback_report_path, "rollback"
    )
    artifact_errors = tuple(
        reason for reason in (adapter_error, rollback_error) if reason
    )
    if artifact_errors:
        return _write_blocked(
            plan, config, output_dir, "blocked_invalid_artifacts",
            "blocked_invalid_artifacts", artifact_errors,
            matched_rule="invalid_input", adapter_report=adapter_report,
            rollback_report=rollback_report, adapter_loaded=adapter_loaded,
            rollback_loaded=rollback_loaded, config_loaded=config_loaded,
            config_present=config_present,
        )

    if config_safety_reasons:
        return _write_blocked(
            plan, config, output_dir, "no_action_taken",
            "blocked_policy_config_safety_boundary", config_safety_reasons,
            matched_rule="policy_config_safety_boundary",
            adapter_report=adapter_report, rollback_report=rollback_report,
            adapter_loaded=adapter_loaded, rollback_loaded=rollback_loaded,
            config_loaded=True, config_present=True, config_boundary=True,
        )

    if not validation.safety_boundary_passed:
        return _write_blocked(
            plan, config, output_dir, "blocked_by_safety_boundary",
            "blocked_by_safety_boundary", validation.safety_failure_reasons,
            matched_rule="runtime_plan_safety_boundary",
            adapter_report=adapter_report, rollback_report=rollback_report,
            adapter_loaded=adapter_loaded, rollback_loaded=rollback_loaded,
            config_loaded=config_loaded, config_present=config_present,
        )

    events: list[dict[str, Any]] = [
        {"event_type": "policy_simulation_started", "status": "ok", "policy_mode": config.policy_mode},
        {"event_type": "runtime_plan_loaded", "status": "ok"},
    ]
    if adapter_loaded:
        events.append({"event_type": "adapter_report_loaded", "status": "ok"})
    if rollback_loaded:
        events.append({"event_type": "rollback_report_loaded", "status": "ok"})
    events.extend((
        {"event_type": "policy_config_loaded", "status": config_status},
        {"event_type": "policy_input_validation_passed", "status": "ok"},
        {"event_type": "policy_evaluation_started", "status": "ok"},
    ))
    decision = evaluate_policy(
        plan,
        config,
        adapter_report,
        rollback_report,
        policy_config_present=config_present,
    )
    events.append({"event_type": "policy_input_summary_built", "status": "ok"})
    for reason in decision.policy_conflict_reasons:
        events.append(
            {
                "event_type": "policy_conflict_detected",
                "status": "warning",
                "reason": reason,
            }
        )
    for field in decision.policy_blocking_inputs:
        events.append(
            {
                "event_type": "policy_blocking_input_detected",
                "status": "blocked",
                "input": field,
            }
        )
    for field in decision.policy_warning_inputs:
        events.append(
            {
                "event_type": "policy_warning_input_detected",
                "status": "warning",
                "input": field,
            }
        )
    matched_rule = first_matched_rule(decision.policy_rule_results)
    events.extend(
        (
            {
                "event_type": "policy_precedence_evaluated",
                "status": "blocked" if decision.policy_status.startswith("blocked_") else "ok",
                "first_matched_rule": matched_rule,
            },
            {"event_type": "policy_decision_path_recorded", "status": "ok"},
        )
    )
    if rollback_report and rollback_report.get("rollback_required") is True:
        events.append({"event_type": "rollback_required_detected", "status": "policy_rollback_required"})
    if rollback_report and rollback_report.get("safe_stop_required") is True:
        events.append({"event_type": "safe_stop_required_detected", "status": "policy_safe_stop_required"})
    events.append({"event_type": "policy_decision_selected", "status": "ok", "selected_policy": decision.selected_policy})
    if decision.policy_status.startswith("blocked_"):
        events.append({"event_type": "policy_simulation_blocked", "status": decision.policy_status})
    else:
        events.append({"event_type": "policy_simulation_completed", "status": "ok"})
    report = build_policy_report(
        plan, adapter_report, rollback_report, decision,
        adapter_report_loaded=adapter_loaded, rollback_report_loaded=rollback_loaded,
        policy_config_loaded=config_loaded,
        policy_config_present=config_present,
    )
    return _write_outcome(PolicySimulationOutcome(decision, report, tuple(events)), output_dir)


def _load_optional_report(path: str | Path | None, kind: str) -> tuple[dict[str, Any] | None, bool, str | None]:
    if path is None:
        return None, False, None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, False, f"invalid_{kind}_report"
    if not isinstance(payload, dict):
        return None, False, f"invalid_{kind}_report:not_object"
    boundary_fields = ("simulation_only", "hardware_control_enabled", "claim_boundary")
    required = boundary_fields + (
        ("adapter_simulation_status", "simulated_actions", "blocked_actions", "adapter_block_reasons")
        if kind == "adapter"
        else (
            "rollback_simulation_status", "rollback_required", "safe_stop_required",
            "no_action_taken", "rollback_strategy", "simulated_revert_actions_planned",
        )
    )
    missing = [field for field in required if field not in payload]
    if missing:
        return payload, True, f"invalid_{kind}_report:missing_required_field:{missing[0]}"
    if (
        payload.get("simulation_only") is not True
        or payload.get("hardware_control_enabled") is not False
        or payload.get("claim_boundary") != CLAIM_BOUNDARY
    ):
        return payload, True, f"invalid_{kind}_report:safety_boundary_failed"
    if kind == "adapter":
        valid_types = (
            isinstance(payload["adapter_simulation_status"], str)
            and _is_count(payload["simulated_actions"])
            and _is_count(payload["blocked_actions"])
            and _is_string_list(payload["adapter_block_reasons"])
        )
    else:
        valid_types = (
            isinstance(payload["rollback_simulation_status"], str)
            and all(isinstance(payload[field], bool) for field in ("rollback_required", "safe_stop_required", "no_action_taken"))
            and isinstance(payload["rollback_strategy"], str)
            and _is_count(payload["simulated_revert_actions_planned"])
        )
    if not valid_types:
        return payload, True, f"invalid_{kind}_report:invalid_field_type"
    return payload, True, None


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _write_blocked(
    plan: Mapping[str, Any] | None,
    config: PolicyConfig,
    output_dir: str | Path,
    selected: str,
    status: str,
    reasons: tuple[str, ...],
    *,
    matched_rule: str,
    plan_loaded: bool = True,
    adapter_report: Mapping[str, Any] | None = None,
    rollback_report: Mapping[str, Any] | None = None,
    adapter_loaded: bool = False,
    rollback_loaded: bool = False,
    config_loaded: bool = True,
    config_present: bool = False,
    config_boundary: bool = False,
    input_scope: str | None = None,
) -> PolicySimulationOutcome:
    rule_results = build_rule_results(
        {matched_rule: reasons[0] if reasons else status}
    )
    blocking_inputs = _blocking_inputs_for(matched_rule, reasons, input_scope)
    warning_inputs = build_warning_inputs(
        plan or {}, adapter_report, rollback_report
    )
    path = build_decision_path(
        plan_loaded=plan_loaded,
        policy_config_present=config_present,
        policy_config_loaded=config_loaded,
        matched_rule=matched_rule,
        selected_policy=selected,
        policy_status=status,
        blocking_reason=reasons[0] if reasons else status,
        blocking_step=(
            "policy_input_validation_failed"
            if matched_rule == "invalid_input"
            else "policy_safety_boundary_failed"
        ),
    )
    decision = PolicyDecision(
        policy_config_id=config.policy_config_id,
        policy_mode=config.policy_mode,
        selected_policy=selected,
        policy_status=status,
        blocked_reasons=reasons,
        policy_decision_path=path,
        policy_blocking_inputs=blocking_inputs,
        policy_warning_inputs=warning_inputs,
        policy_rule_results=rule_results,
    )
    reason = reasons[0] if reasons else status
    failed_event = "policy_safety_boundary_failed" if config_boundary or status == "blocked_by_safety_boundary" else "policy_input_validation_failed"
    events: list[dict[str, Any]] = [
        {"event_type": "policy_simulation_started", "status": "ok", "policy_mode": config.policy_mode},
        {"event_type": failed_event, "status": "blocked" if "boundary" in status else status, "reason": reason},
        {"event_type": "policy_input_summary_built", "status": "ok"},
    ]
    for field in blocking_inputs:
        events.append(
            {
                "event_type": "policy_blocking_input_detected",
                "status": "blocked",
                "input": field,
            }
        )
    for field in warning_inputs:
        events.append(
            {
                "event_type": "policy_warning_input_detected",
                "status": "warning",
                "input": field,
            }
        )
    events.extend(
        (
            {
                "event_type": "policy_precedence_evaluated",
                "status": "blocked",
                "first_matched_rule": matched_rule,
            },
            {"event_type": "policy_decision_path_recorded", "status": "ok"},
            {"event_type": "policy_simulation_blocked", "status": status},
        )
    )
    report = build_policy_report(
        plan, adapter_report, rollback_report, decision,
        plan_loaded=plan_loaded, adapter_report_loaded=adapter_loaded,
        rollback_report_loaded=rollback_loaded, policy_config_loaded=config_loaded,
        policy_config_present=config_present,
    )
    return _write_outcome(
        PolicySimulationOutcome(decision, report, tuple(events)), output_dir
    )


def _blocking_inputs_for(
    matched_rule: str, reasons: tuple[str, ...], input_scope: str | None = None
) -> tuple[str, ...]:
    if matched_rule == "policy_config_safety_boundary":
        mapping = {
            "simulation_only_must_be_true": "policy_config.simulation_only",
            "hardware_control_enabled_must_be_false": "policy_config.hardware_control_enabled",
            "claim_boundary_must_be_simulation_only_not_certified": "policy_config.claim_boundary",
            "allow_real_execution_must_be_false": "policy_config.allow_real_execution",
            "allow_hardware_control_must_be_false": "policy_config.allow_hardware_control",
            "allow_retry_must_be_false": "policy_config.allow_retry",
        }
        return tuple(dict.fromkeys(mapping.get(reason, "policy_config") for reason in reasons))
    if matched_rule == "runtime_plan_safety_boundary":
        mapping = {
            "hardware_control_enabled_must_be_false": "runtime_plan.hardware_control_enabled",
            "claim_boundary_must_be_simulation_only_not_certified": "runtime_plan.claim_boundary",
            "execution_mode_must_be_dry_run": "runtime_plan.execution_mode",
            "human_review_required_must_be_true": "runtime_plan.human_review_required",
        }
        return tuple(dict.fromkeys(mapping.get(reason, "runtime_plan") for reason in reasons))
    inputs: list[str] = []
    for reason in reasons:
        if input_scope == "policy_config":
            field = reason.split(":", 1)[1] if reason.startswith("missing_required_field:") else ""
            inputs.append(f"policy_config.{field}" if field else "policy_config")
            continue
        if reason.startswith("missing_required_field:"):
            inputs.append(f"runtime_plan.{reason.split(':', 1)[1]}")
        elif "adapter_report" in reason:
            inputs.append("adapter_report")
        elif "rollback_report" in reason:
            inputs.append("rollback_report")
        elif "policy_config" in reason:
            inputs.append("policy_config")
        else:
            inputs.append("runtime_plan")
    return tuple(dict.fromkeys(inputs))


def _write_outcome(outcome: PolicySimulationOutcome, output_dir: str | Path) -> PolicySimulationOutcome:
    output = Path(output_dir)
    write_policy_trace(output / "policy_trace.jsonl", outcome.trace_events)
    write_json(output / "policy_decision.json", outcome.decision.to_dict())
    write_json(output / "policy_report.json", outcome.report.to_dict())
    return outcome
