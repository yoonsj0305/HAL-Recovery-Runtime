"""Orchestration for plan-only and dry-run artifact generation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .bundle_loader import load_compiler_bundle
from .bundle_validator import validate_compiler_bundle
from .compatibility import check_compatibility
from .event_log import write_events, write_json
from .models import DryRunResult, RuntimePlan, RuntimeReport, SafetyGateResult
from .plan_builder import build_runtime_plan
from .profile_loader import load_profile
from .report import build_runtime_report
from .safety_gate import SafetyGate


def prepare_plan(profile_path: str | Path) -> tuple[RuntimePlan, SafetyGateResult]:
    profile = load_profile(profile_path)
    gate_result = SafetyGate().evaluate(profile)
    return build_runtime_plan(profile, gate_result), gate_result


def write_plan_artifact(profile_path: str | Path, output_dir: str | Path) -> tuple[RuntimePlan, SafetyGateResult]:
    plan, gate_result = prepare_plan(profile_path)
    write_json(Path(output_dir) / "runtime_plan.json", plan.to_dict())
    return plan, gate_result


def run_dry_run(profile_path: str | Path, output_dir: str | Path) -> DryRunResult:
    profile = load_profile(profile_path)
    result = _simulate_profile(profile)
    _write_dry_run_result(result, output_dir)
    return result


def _simulate_profile(profile: dict[str, Any]) -> DryRunResult:
    events: list[dict[str, Any]] = [
        {
            "event_type": "profile_loaded",
            "status": "ok",
            "hardware_control_enabled": profile.get("hardware_control_enabled"),
        }
    ]
    gate_result = SafetyGate().evaluate(profile)

    if gate_result.passed:
        events.append({"event_type": "safety_gate_passed", "status": "ok"})
    else:
        events.append(
            {
                "event_type": "safety_gate_failed",
                "status": "blocked",
                "reason": gate_result.failure_reasons[0],
                "reasons": list(gate_result.failure_reasons),
            }
        )

    plan = build_runtime_plan(profile, gate_result)
    if gate_result.passed:
        events.append(
            {
                "event_type": "plan_built",
                "status": "planned",
                "plan_status": plan.plan_status,
            }
        )
        if gate_result.degraded_mode:
            events.append(
                {
                    "event_type": "degraded_mode_entered",
                    "status": "degraded",
                    "reason": "preferred_routes_missing",
                }
            )
        for action in plan.actions:
            events.append(
                {
                    "event_type": "action_planned",
                    "status": "planned",
                    "action_type": action.action_type,
                    "workload_id": action.workload_id,
                }
            )
        for action in plan.blocked_actions:
            events.append(
                {
                    "event_type": "action_blocked",
                    "status": "blocked",
                    "action_type": action.action_type,
                    "workload_id": action.workload_id,
                    "reason": action.reason,
                }
            )

    report = build_runtime_report(plan, gate_result)
    if gate_result.passed:
        events.append(
            {
                "event_type": "dry_run_completed",
                "status": (
                    "degraded"
                    if gate_result.degraded_mode
                    else "ok" if not plan.blocked_actions else "completed_with_blocks"
                ),
            }
        )
    else:
        events.append(
            {
                "event_type": "dry_run_blocked",
                "status": "blocked_by_safety_gate",
            }
        )

    return DryRunResult(plan=plan, report=report, events=tuple(events))


def run_bundle_dry_run(
    bundle_path: str | Path, output_dir: str | Path
) -> DryRunResult:
    bundle = load_compiler_bundle(bundle_path)
    compatibility = (
        check_compatibility(bundle.recovery_profile)
        if bundle.recovery_profile is not None
        else None
    )
    validation = validate_compiler_bundle(bundle)
    bundle_events: list[dict[str, Any]] = [
        {
            "event_type": "bundle_loaded",
            "status": "ok" if not bundle.load_errors else "loaded_with_errors",
            "present_artifacts": list(bundle.present_artifacts),
        }
    ]
    if compatibility is not None:
        bundle_events.append(
            {
                "event_type": (
                    "compatibility_check_passed"
                    if compatibility.compatible
                    else "compatibility_check_failed"
                ),
                "status": "ok" if compatibility.compatible else "blocked",
            }
        )

    if not validation.bundle_validation_passed:
        bundle_events.append(
            {
                "event_type": "bundle_validation_failed",
                "status": "blocked",
                "bundle_validation_status": validation.bundle_validation_status,
            }
        )
        profile = bundle.recovery_profile or {}
        plan = RuntimePlan(
            profile_id=str(profile.get("profile_id", "unknown")),
            hardware_control_enabled=profile.get("hardware_control_enabled") is not False,
            human_review_required=profile.get("human_review_required") is True,
            claim_boundary=(
                profile.get("claim_boundary")
                if isinstance(profile.get("claim_boundary"), str)
                else None
            ),
            plan_status="blocked_by_bundle_validation",
            plan_block_reasons=validation.bundle_validation_reasons,
        )
        report = RuntimeReport(
            profile_loaded=bundle.recovery_profile is not None,
            safety_gate_passed=False,
            planned_actions=0,
            blocked_actions=0,
            degraded_mode_entered=False,
            runtime_status="blocked_by_bundle_validation",
            hardware_control_enabled=plan.hardware_control_enabled,
            human_review_required=plan.human_review_required,
            claim_boundary=plan.claim_boundary,
            safety_gate_evaluated=False,
            bundle_gate_evaluated=True,
            execution_gate_stage="bundle_validation_gate",
            bundle_mode=True,
            bundle_validation_passed=False,
            bundle_validation_status=validation.bundle_validation_status,
            bundle_validation_reasons=validation.bundle_validation_reasons,
            bundle_validation_warnings=validation.bundle_validation_warnings,
            present_artifacts=validation.present_artifacts,
            missing_artifacts=validation.missing_artifacts,
            degraded_bundle_mode=False,
            supporting_artifact_count=validation.supporting_artifact_count,
        )
        bundle_events.append(
            {
                "event_type": "dry_run_blocked",
                "status": "blocked_by_bundle_validation",
            }
        )
        result = DryRunResult(plan=plan, report=report, events=tuple(bundle_events))
        _write_dry_run_result(result, output_dir)
        return result

    assert bundle.recovery_profile is not None
    base = _simulate_profile(bundle.recovery_profile)
    if validation.degraded_bundle_mode:
        bundle_event_type = "bundle_validation_degraded"
        bundle_event_status = "degraded"
    else:
        bundle_event_type = "bundle_validation_passed"
        bundle_event_status = "ok"
    bundle_events.append(
        {
            "event_type": bundle_event_type,
            "status": bundle_event_status,
            "bundle_validation_status": validation.bundle_validation_status,
        }
    )

    runtime_status = base.report.runtime_status
    if (
        validation.degraded_bundle_mode or validation.bundle_validation_warnings
    ) and runtime_status == "dry_run_passed":
        runtime_status = "dry_run_passed_with_bundle_warnings"
    if not base.report.safety_gate_passed:
        execution_gate_stage = "bundle_safety_gate"
    elif base.report.degraded_mode_entered:
        execution_gate_stage = "plan_builder"
    else:
        execution_gate_stage = "dry_run_completed"
    report = replace(
        base.report,
        runtime_status=runtime_status,
        safety_gate_evaluated=True,
        bundle_gate_evaluated=True,
        execution_gate_stage=execution_gate_stage,
        bundle_mode=True,
        bundle_validation_passed=True,
        bundle_validation_status=validation.bundle_validation_status,
        bundle_validation_reasons=validation.bundle_validation_reasons,
        bundle_validation_warnings=validation.bundle_validation_warnings,
        present_artifacts=validation.present_artifacts,
        missing_artifacts=validation.missing_artifacts,
        degraded_bundle_mode=validation.degraded_bundle_mode,
        supporting_artifact_count=validation.supporting_artifact_count,
    )
    result = DryRunResult(
        plan=base.plan,
        report=report,
        events=tuple(bundle_events) + base.events,
    )
    _write_dry_run_result(result, output_dir)
    return result


def _write_dry_run_result(result: DryRunResult, output_dir: str | Path) -> None:
    output_path = Path(output_dir)
    write_json(output_path / "runtime_plan.json", result.plan.to_dict())
    write_events(output_path / "runtime_events.jsonl", result.events)
    write_json(output_path / "runtime_report.json", result.report.to_dict())
