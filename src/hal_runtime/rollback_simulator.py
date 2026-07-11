"""Orchestrate failure injection and simulation-only rollback planning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapter_simulator import PlanLoadError, load_runtime_plan, validate_runtime_plan
from .event_log import write_json
from .failure_injector import inject_failure
from .failure_models import (
    FailureInjectionResult,
    FailureScenario,
    ScenarioLoadError,
    default_failure_scenario,
    load_failure_scenario,
    scenario_from_mapping,
    validate_failure_scenario,
)
from .failure_modes import supported_failure_modes
from .failure_trace import write_failure_trace
from .rollback_models import FailureSimulationOutcome, RollbackPlan
from .rollback_planner import NONEXECUTABLE_PLAN_STATUSES, build_rollback_plan
from .rollback_report import build_rollback_report


def simulate_failure_file(
    plan_path: str | Path,
    output_dir: str | Path,
    scenario_path: str | Path | None = None,
) -> FailureSimulationOutcome:
    try:
        plan = load_runtime_plan(plan_path)
    except PlanLoadError as exc:
        scenario = default_failure_scenario()
        outcome = _blocked_outcome(
            None,
            scenario,
            "invalid_plan",
            "invalid_plan",
            (str(exc),),
            plan_loaded=False,
            trace=(
                {"event_type": "plan_validation_failed", "status": "invalid_plan", "reason": str(exc)},
                {"event_type": "failure_simulation_blocked", "status": "invalid_plan"},
            ),
        )
        return _write_outcome(outcome, output_dir)

    validation = validate_runtime_plan(plan)
    scenario, scenario_loaded, scenario_reasons, scenario_status = _load_scenario(
        scenario_path
    )
    start = {
        "event_type": "failure_simulation_started",
        "status": "ok",
        "failure_mode": scenario.failure_mode,
    }
    plan_event = {"event_type": "plan_loaded", "status": "ok"}

    if not validation.structurally_valid:
        outcome = _blocked_outcome(
            plan,
            scenario,
            "invalid_plan",
            "invalid_plan",
            validation.validation_reasons,
            scenario_loaded=scenario_loaded,
            trace=(
                start,
                plan_event,
                {
                    "event_type": "plan_validation_failed",
                    "status": "invalid_plan",
                    "reason": validation.validation_reasons[0],
                },
                {"event_type": "failure_simulation_blocked", "status": "invalid_plan"},
            ),
        )
        return _write_outcome(outcome, output_dir)

    if not validation.safety_boundary_passed:
        outcome = _blocked_outcome(
            plan,
            scenario,
            "blocked_safety_boundary",
            "blocked_plan_safety_boundary",
            validation.safety_failure_reasons,
            scenario_loaded=scenario_loaded,
            trace=(
                start,
                plan_event,
                {
                    "event_type": "plan_safety_boundary_failed",
                    "status": "blocked",
                    "reason": validation.safety_failure_reasons[0],
                },
                {
                    "event_type": "failure_simulation_blocked",
                    "status": "blocked_plan_safety_boundary",
                },
            ),
        )
        return _write_outcome(outcome, output_dir)

    if scenario_reasons:
        outcome = _blocked_outcome(
            plan,
            scenario,
            "blocked_safety_boundary",
            "blocked_scenario_safety_boundary",
            scenario_reasons,
            scenario_loaded=scenario_loaded,
            trace=(
                start,
                plan_event,
                {
                    "event_type": "scenario_safety_boundary_failed",
                    "status": "blocked",
                    "reason": scenario_reasons[0],
                },
                {
                    "event_type": "failure_simulation_blocked",
                    "status": "blocked_scenario_safety_boundary",
                },
            ),
        )
        return _write_outcome(outcome, output_dir)

    scenario_event = {
        "event_type": "scenario_loaded",
        "status": scenario_status,
    }
    if plan["plan_status"] in NONEXECUTABLE_PLAN_STATUSES:
        reason = f"source_plan_not_executable:{plan['plan_status']}"
        injection = FailureInjectionResult((), (), (), (reason,), "no_action_taken", None, ())
        rollback_plan = build_rollback_plan(plan, scenario, injection)
        report = build_rollback_report(plan, scenario, injection, rollback_plan)
        outcome = FailureSimulationOutcome(
            rollback_plan,
            report,
            (
                start,
                plan_event,
                scenario_event,
                {"event_type": "source_plan_not_executable", "status": "no_action_taken", "plan_status": plan["plan_status"]},
                {"event_type": "no_action_taken", "status": "ok", "reason": f"source_plan_not_executable:{plan['plan_status']}"},
                {"event_type": "failure_simulation_completed", "status": "ok"},
            ),
        )
        return _write_outcome(outcome, output_dir)

    injection = inject_failure(plan, scenario)
    rollback_plan = build_rollback_plan(plan, scenario, injection)
    report = build_rollback_report(plan, scenario, injection, rollback_plan)
    events: list[dict[str, Any]] = [start, plan_event, scenario_event]
    for action_id, action_status in injection.action_outcomes:
        if action_status == "simulated":
            events.append({"event_type": "action_simulated", "status": "simulated", "action_id": action_id})
        elif action_status == "failed":
            events.append(
                {
                    "event_type": "failure_injected",
                    "status": "failed",
                    "failure_mode": scenario.failure_mode,
                    "action_id": action_id,
                }
            )
        else:
            events.append({"event_type": "action_skipped", "status": "skipped", "action_id": action_id})
    revert_actions = tuple(
        action
        for action in rollback_plan.rollback_actions
        if action.rollback_action_type == "simulated_revert"
    )
    safe_stop_actions = tuple(
        action
        for action in rollback_plan.rollback_actions
        if action.rollback_action_type == "safe_stop_marker"
    )
    if revert_actions:
        events.append({"event_type": "rollback_planning_started", "status": "ok"})
        for action in revert_actions:
            events.append(
                {
                    "event_type": "rollback_action_planned",
                    "status": "planned",
                    "rollback_action_type": action.rollback_action_type,
                    "source_action_id": action.source_action_id,
                }
            )
        events.append({"event_type": "rollback_plan_completed", "status": "ok"})
    if safe_stop_actions:
        events.append(
            {
                "event_type": "safe_stop_planning_started",
                "status": "ok",
                "reason": scenario.failure_mode,
            }
        )
        for action in safe_stop_actions:
            events.append(
                {
                    "event_type": "rollback_action_planned",
                    "status": "planned",
                    "rollback_action_type": "safe_stop_marker",
                    "source_action_id": action.source_action_id,
                }
            )
        events.append({"event_type": "safe_stop_plan_completed", "status": "ok"})
    if report.rollback_simulation_status == "rollback_not_required":
        events.append({"event_type": "rollback_not_required", "status": "ok"})
    elif rollback_plan.no_action_taken:
        events.append(
            {
                "event_type": "no_action_taken",
                "status": "ok",
                "reason": scenario.failure_mode,
            }
        )
    events.append({"event_type": "failure_simulation_completed", "status": "ok"})
    return _write_outcome(
        FailureSimulationOutcome(rollback_plan, report, tuple(events)), output_dir
    )


def _load_scenario(
    scenario_path: str | Path | None,
) -> tuple[FailureScenario, bool, tuple[str, ...], str]:
    if scenario_path is None:
        return default_failure_scenario(), True, (), "default_none"
    try:
        raw = load_failure_scenario(scenario_path)
    except ScenarioLoadError as exc:
        return default_failure_scenario(), False, (str(exc),), "invalid"
    validation = validate_failure_scenario(raw, supported_failure_modes())
    if not validation.valid:
        return _invalid_scenario(raw), True, validation.reasons, "invalid"
    return scenario_from_mapping(raw), True, (), "ok"


def _invalid_scenario(raw: dict[str, Any]) -> FailureScenario:
    mode = raw.get("failure_mode")
    return FailureScenario(
        scenario_id=str(raw.get("scenario_id", "SCN_INVALID")),
        failure_mode=mode if isinstance(mode, str) else "unknown",
        injection_stage=str(raw.get("injection_stage", "unknown")),
        simulation_only=raw.get("simulation_only") is True,
        hardware_control_enabled=raw.get("hardware_control_enabled") is True,
        claim_boundary=str(raw.get("claim_boundary", "unknown")),
    )


def _blocked_outcome(
    plan: dict[str, Any] | None,
    scenario: FailureScenario,
    rollback_plan_status: str,
    report_status: str,
    reasons: tuple[str, ...],
    *,
    plan_loaded: bool = True,
    scenario_loaded: bool = True,
    trace: tuple[dict[str, Any], ...],
) -> FailureSimulationOutcome:
    source_status = str(plan.get("plan_status", "unknown")) if plan else "unknown"
    rollback_plan = RollbackPlan(
        source_plan_status=source_status,
        scenario_id=scenario.scenario_id,
        failure_mode=scenario.failure_mode,
        rollback_required=False,
        safe_stop_required=False,
        no_action_taken=True,
        rollback_plan_status=rollback_plan_status,
        rollback_strategy="no_action_taken",
    )
    injection = FailureInjectionResult((), (), (), reasons, "no_action_taken", None, ())
    report = build_rollback_report(
        plan,
        scenario,
        injection,
        rollback_plan,
        plan_loaded=plan_loaded,
        scenario_loaded=scenario_loaded,
        status_override=report_status,
        failure_reasons_override=reasons,
    )
    events = list(trace)
    if not any(event.get("event_type") == "no_action_taken" for event in events):
        insert_at = max(len(events) - 1, 0)
        events.insert(
            insert_at,
            {
                "event_type": "no_action_taken",
                "status": report_status,
                "reason": reasons[0] if reasons else "blocked_before_simulation",
            },
        )
    return FailureSimulationOutcome(rollback_plan, report, tuple(events))


def _write_outcome(
    outcome: FailureSimulationOutcome, output_dir: str | Path
) -> FailureSimulationOutcome:
    output = Path(output_dir)
    write_failure_trace(output / "failure_trace.jsonl", outcome.trace_events)
    write_json(output / "rollback_plan.json", outcome.rollback_plan.to_dict())
    write_json(output / "rollback_report.json", outcome.rollback_report.to_dict())
    return outcome
