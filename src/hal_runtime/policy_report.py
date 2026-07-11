"""Build bounded reports for policy simulation decisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapter_report import build_source_plan_summary
from .policy_audit import build_policy_input_summary
from .policy_models import PolicyDecision, PolicyReport


def build_policy_report(
    plan: Mapping[str, Any] | None,
    adapter_report: Mapping[str, Any] | None,
    rollback_report: Mapping[str, Any] | None,
    decision: PolicyDecision,
    *,
    plan_loaded: bool = True,
    adapter_report_loaded: bool = False,
    rollback_report_loaded: bool = False,
    policy_config_loaded: bool = True,
    policy_config_present: bool = False,
) -> PolicyReport:
    confidence = (
        "blocked_or_invalid"
        if decision.policy_status.startswith("blocked_") or decision.policy_status == "invalid_policy_input"
        else "simulation_only_low_certainty"
    )
    return PolicyReport(
        plan_loaded=plan_loaded,
        adapter_report_loaded=adapter_report_loaded,
        rollback_report_loaded=rollback_report_loaded,
        policy_config_loaded=policy_config_loaded,
        decision=decision,
        source_plan_summary=build_source_plan_summary(plan),
        adapter_report_summary=_adapter_summary(adapter_report),
        rollback_report_summary=_rollback_summary(rollback_report),
        policy_input_summary=build_policy_input_summary(
            plan,
            adapter_report,
            rollback_report,
            policy_config_present=policy_config_present,
            policy_mode=decision.policy_mode,
        ),
        decision_confidence=confidence,
    )


def _adapter_summary(report: Mapping[str, Any] | None) -> dict[str, Any]:
    return {
        "adapter_simulation_status": report.get("adapter_simulation_status") if report else None,
        "simulated_actions": report.get("simulated_actions", 0) if report else 0,
        "blocked_actions": report.get("blocked_actions", 0) if report else 0,
        "adapter_block_reasons": list(report.get("adapter_block_reasons", [])) if report else [],
    }


def _rollback_summary(report: Mapping[str, Any] | None) -> dict[str, Any]:
    return {
        "rollback_simulation_status": report.get("rollback_simulation_status") if report else None,
        "rollback_required": report.get("rollback_required", False) if report else False,
        "safe_stop_required": report.get("safe_stop_required", False) if report else False,
        "no_action_taken": report.get("no_action_taken", False) if report else False,
        "rollback_strategy": report.get("rollback_strategy", "none") if report else "none",
    }
