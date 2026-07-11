"""Data models for the simulation-only policy decision layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adapter_models import CLAIM_BOUNDARY, SourcePlanSummary
from .models import RUNTIME_VERSION
from .policy_audit import POLICY_PRECEDENCE_ORDER


POLICY_SIMULATION_VERSION = RUNTIME_VERSION
POLICY_AUDIT_VERSION = RUNTIME_VERSION
POLICY_LIMITATIONS = (
    "simulation_only",
    "not_certified",
    "no_" + "real_policy_" + "enforcement",
    "no_hardware_control",
)


@dataclass(frozen=True)
class PolicyConfig:
    policy_config_id: str
    policy_mode: str
    human_review_required: bool
    allow_retry: bool
    allow_real_execution: bool
    allow_hardware_control: bool
    simulation_only: bool
    hardware_control_enabled: bool
    claim_boundary: str
    max_allowed_blocked_actions: int = 0
    max_allowed_degraded_flags: int = 0
    notes: str | None = None


@dataclass(frozen=True)
class PolicyConfigValidation:
    structurally_valid: bool
    safety_boundary_passed: bool
    structural_reasons: tuple[str, ...] = ()
    safety_reasons: tuple[str, ...] = ()

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.structural_reasons + self.safety_reasons


@dataclass(frozen=True)
class PolicyDecision:
    policy_config_id: str
    policy_mode: str
    selected_policy: str
    policy_status: str
    human_review_required: bool = True
    retry_allowed: bool = False
    real_execution_allowed: bool = False
    hardware_control_allowed: bool = False
    policy_reasons: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    warning_reasons: tuple[str, ...] = ()
    policy_decision_path: tuple[dict[str, Any], ...] = ()
    policy_conflict_reasons: tuple[str, ...] = ()
    policy_blocking_inputs: tuple[str, ...] = ()
    policy_warning_inputs: tuple[str, ...] = ()
    policy_rule_results: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": RUNTIME_VERSION,
            "policy_simulation_version": POLICY_SIMULATION_VERSION,
            "policy_audit_version": POLICY_AUDIT_VERSION,
            "simulation_only": True,
            "hardware_control_enabled": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "policy_config_id": self.policy_config_id,
            "policy_mode": self.policy_mode,
            "selected_policy": self.selected_policy,
            "policy_status": self.policy_status,
            "human_review_required": self.human_review_required,
            "retry_allowed": self.retry_allowed,
            "real_execution_allowed": self.real_execution_allowed,
            "hardware_control_allowed": self.hardware_control_allowed,
            "policy_reasons": list(self.policy_reasons),
            "blocked_reasons": list(self.blocked_reasons),
            "warning_reasons": list(self.warning_reasons),
            "policy_precedence_order": list(POLICY_PRECEDENCE_ORDER),
            "policy_decision_path": [dict(step) for step in self.policy_decision_path],
            "policy_conflict_reasons": list(self.policy_conflict_reasons),
            "policy_blocking_inputs": list(self.policy_blocking_inputs),
            "policy_warning_inputs": list(self.policy_warning_inputs),
            "known_limitations": list(POLICY_LIMITATIONS),
        }


@dataclass(frozen=True)
class PolicyReport:
    plan_loaded: bool
    adapter_report_loaded: bool
    rollback_report_loaded: bool
    policy_config_loaded: bool
    decision: PolicyDecision
    source_plan_summary: SourcePlanSummary
    adapter_report_summary: dict[str, Any]
    rollback_report_summary: dict[str, Any]
    policy_input_summary: dict[str, Any]
    decision_confidence: str

    def to_dict(self) -> dict[str, Any]:
        decision = self.decision.to_dict()
        return {
            "runtime_version": RUNTIME_VERSION,
            "policy_simulation_version": POLICY_SIMULATION_VERSION,
            "policy_audit_version": POLICY_AUDIT_VERSION,
            "simulation_only": True,
            "hardware_control_enabled": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "plan_loaded": self.plan_loaded,
            "adapter_report_loaded": self.adapter_report_loaded,
            "rollback_report_loaded": self.rollback_report_loaded,
            "policy_config_loaded": self.policy_config_loaded,
            "policy_config_id": self.decision.policy_config_id,
            "policy_mode": self.decision.policy_mode,
            "selected_policy": self.decision.selected_policy,
            "policy_status": self.decision.policy_status,
            "human_review_required": self.decision.human_review_required,
            "retry_allowed": self.decision.retry_allowed,
            "real_execution_allowed": self.decision.real_execution_allowed,
            "hardware_control_allowed": self.decision.hardware_control_allowed,
            "source_plan_summary": self.source_plan_summary.to_dict(),
            "adapter_report_summary": self.adapter_report_summary,
            "rollback_report_summary": self.rollback_report_summary,
            "policy_input_summary": self.policy_input_summary,
            "policy_reasons": decision["policy_reasons"],
            "blocked_reasons": decision["blocked_reasons"],
            "warning_reasons": decision["warning_reasons"],
            "policy_precedence_order": decision["policy_precedence_order"],
            "policy_decision_path": decision["policy_decision_path"],
            "policy_conflict_reasons": decision["policy_conflict_reasons"],
            "policy_blocking_inputs": decision["policy_blocking_inputs"],
            "policy_warning_inputs": decision["policy_warning_inputs"],
            "policy_rule_results": [dict(result) for result in self.decision.policy_rule_results],
            "decision_confidence": self.decision_confidence,
            "known_limitations": decision["known_limitations"],
        }


@dataclass(frozen=True)
class PolicySimulationOutcome:
    decision: PolicyDecision
    report: PolicyReport
    trace_events: tuple[dict[str, Any], ...]
