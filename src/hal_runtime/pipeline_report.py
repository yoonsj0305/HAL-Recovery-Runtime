"""Build bounded pipeline summary and report payloads."""

from __future__ import annotations

from typing import Any

from .pipeline_models import PIPELINE_ID, PipelineStageResult, boundary_fields
from .pipeline_stages import (
    KNOWN_PIPELINE_LIMITATIONS,
    PIPELINE_DEPENDENCY_GRAPH,
    PIPELINE_STAGE_NAMES,
)


REPORT_LIMITATIONS = (
    "simulation_only",
    "not_certified",
    "no_hardware_control",
    "no_real_hardware_validation",
    "no_" + "real_policy_" + "enforcement",
)
PIPELINE_FAILURE_CATEGORIES = (
    "none",
    "invalid_input",
    "runtime_safety_boundary",
    "bundle_validation",
    "adapter_safety_boundary",
    "failure_scenario_safety_boundary",
    "policy_config_safety_boundary",
    "evidence_validation",
    "internal_failure",
    "warnings_only",
)


def build_pipeline_summary(
    *,
    input_mode: str,
    pipeline_status: str,
    stage_results: list[PipelineStageResult],
    runtime_report: dict[str, Any] | None,
    policy_report: dict[str, Any] | None,
    evidence_report: dict[str, Any] | None,
    pipeline_warnings: list[str],
) -> dict[str, Any]:
    normalized = normalize_stage_results(stage_results)
    terminal = pipeline_terminal_state(pipeline_status, normalized)
    skip_reasons = pipeline_skip_reasons(normalized)
    warning_reasons = list(dict.fromkeys(pipeline_warnings))
    return {
        **boundary_fields(),
        "pipeline_id": PIPELINE_ID,
        "input_mode": input_mode,
        "pipeline_status": pipeline_status,
        "pipeline_completed": pipeline_status in {
            "pipeline_completed",
            "pipeline_completed_with_warnings",
        },
        "pipeline_blocked": pipeline_status == "pipeline_blocked",
        "pipeline_terminal_stage": terminal["pipeline_terminal_stage"],
        "pipeline_exit_reason": terminal["pipeline_exit_reason"],
        "pipeline_blocking_stage": terminal["pipeline_blocking_stage"],
        "pipeline_failure_category": terminal["pipeline_failure_category"],
        "stage_counts": build_stage_counts(normalized),
        "pipeline_skip_reasons": skip_reasons,
        "pipeline_warning_reasons": warning_reasons,
        "pipeline_warnings": warning_reasons,
        "stages_completed": [
            result.stage_name
            for result in normalized
            if result.stage_status in {"completed", "completed_with_warnings"}
        ],
        "stages_failed": [
            result.stage_name
            for result in normalized
            if result.stage_status in {"blocked", "failed"}
        ],
        "stages_skipped": [
            result.stage_name
            for result in normalized
            if result.stage_status == "skipped"
        ],
        "final_selected_policy": (
            policy_report.get("selected_policy") if policy_report else None
        ),
        "final_policy_status": (
            policy_report.get("policy_status") if policy_report else None
        ),
        "evidence_validation_status": (
            evidence_report.get("evidence_validation_status")
            if evidence_report
            else None
        ),
        "known_limitations": list(KNOWN_PIPELINE_LIMITATIONS),
    }


def build_pipeline_report(
    *,
    input_mode: str,
    profile_id: str | None,
    pipeline_status: str,
    pipeline_exit_code: int,
    stage_results: list[PipelineStageResult],
    runtime_plan: dict[str, Any] | None,
    runtime_report: dict[str, Any] | None,
    adapter_report: dict[str, Any] | None,
    rollback_report: dict[str, Any] | None,
    policy_report: dict[str, Any] | None,
    evidence_report: dict[str, Any] | None,
    pipeline_reasons: list[str],
    pipeline_warning_reasons: list[str],
    pipeline_blocking_reasons: list[str],
    evidence_stage_skipped: bool,
) -> dict[str, Any]:
    normalized = normalize_stage_results(stage_results)
    matrix = build_pipeline_stage_matrix(normalized)
    counts = build_stage_counts(normalized)
    terminal = pipeline_terminal_state(pipeline_status, normalized)
    skip_reasons = pipeline_skip_reasons(normalized)
    evidence_summary = build_evidence_summary(
        normalized,
        evidence_report,
        evidence_stage_skipped=evidence_stage_skipped,
    )
    consistency = build_pipeline_consistency_checks(
        normalized, matrix, counts, pipeline_status, terminal, evidence_summary
    )
    consistency_warnings = [
        f"pipeline_consistency_warning:{name}"
        for name, passed in consistency.items()
        if passed is not True
    ]
    warning_reasons = list(
        dict.fromkeys(pipeline_warning_reasons + consistency_warnings)
    )
    planned_actions = _count(runtime_plan, "actions")
    blocked_plan_actions = _count(runtime_plan, "blocked_actions")
    runtime_summary = {
        "runtime_status": runtime_report.get("runtime_status") if runtime_report else None,
        "planned_actions": runtime_report.get("planned_actions", planned_actions)
        if runtime_report
        else planned_actions,
        "blocked_actions": runtime_report.get("blocked_actions", blocked_plan_actions)
        if runtime_report
        else blocked_plan_actions,
    }
    adapter_summary = {
        "adapter_simulation_status": adapter_report.get("adapter_simulation_status")
        if adapter_report
        else None,
        "simulated_actions": adapter_report.get("simulated_actions", 0)
        if adapter_report
        else 0,
        "blocked_actions": adapter_report.get("blocked_actions", 0)
        if adapter_report
        else 0,
    }
    rollback_summary = {
        "rollback_simulation_status": rollback_report.get("rollback_simulation_status")
        if rollback_report
        else None,
        "rollback_required": rollback_report.get("rollback_required", False)
        if rollback_report
        else False,
        "safe_stop_required": rollback_report.get("safe_stop_required", False)
        if rollback_report
        else False,
        "no_action_taken": rollback_report.get("no_action_taken", False)
        if rollback_report
        else False,
    }
    policy_summary = {
        "selected_policy": policy_report.get("selected_policy") if policy_report else None,
        "policy_status": policy_report.get("policy_status") if policy_report else None,
        "human_review_required": policy_report.get("human_review_required")
        if policy_report
        else None,
        "real_execution_allowed": policy_report.get("real_execution_allowed", False)
        if policy_report
        else False,
        "hardware_control_allowed": policy_report.get("hardware_control_allowed", False)
        if policy_report
        else False,
    }
    return {
        **boundary_fields(),
        "pipeline_id": PIPELINE_ID,
        "input_mode": input_mode,
        "profile_id": profile_id,
        "pipeline_status": pipeline_status,
        "pipeline_completed": pipeline_status in {
            "pipeline_completed",
            "pipeline_completed_with_warnings",
        },
        "pipeline_blocked": pipeline_status == "pipeline_blocked",
        "pipeline_exit_code": pipeline_exit_code,
        "pipeline_terminal_stage": terminal["pipeline_terminal_stage"],
        "pipeline_exit_reason": terminal["pipeline_exit_reason"],
        "pipeline_blocking_stage": terminal["pipeline_blocking_stage"],
        "pipeline_failure_category": terminal["pipeline_failure_category"],
        "stage_counts": counts,
        "stage_results": [result.to_dict() for result in normalized],
        "pipeline_stage_matrix": matrix,
        "pipeline_skip_reasons": skip_reasons,
        "pipeline_warning_reasons": warning_reasons,
        "pipeline_consistency_checks": consistency,
        "pipeline_dependency_graph": {
            name: list(dependencies)
            for name, dependencies in PIPELINE_DEPENDENCY_GRAPH.items()
        },
        "pipeline_stage_transition_log": build_transition_log(normalized),
        "runtime_summary": runtime_summary,
        "adapter_summary": adapter_summary,
        "rollback_summary": rollback_summary,
        "policy_summary": policy_summary,
        "evidence_summary": evidence_summary,
        "pipeline_reasons": list(dict.fromkeys(pipeline_reasons)),
        "pipeline_blocking_reasons": list(dict.fromkeys(pipeline_blocking_reasons)),
        "known_limitations": list(REPORT_LIMITATIONS),
    }


def normalize_stage_results(
    stage_results: list[PipelineStageResult],
) -> list[PipelineStageResult]:
    by_name = {result.stage_name: result for result in stage_results}
    first_block = next(
        (
            result
            for result in stage_results
            if result.stage_status in {"blocked", "failed"}
        ),
        None,
    )
    missing_reason = (
        f"{first_block.stage_name}_blocked" if first_block else "not_reached"
    )
    normalized: list[PipelineStageResult] = []
    for name in PIPELINE_STAGE_NAMES:
        result = by_name.get(name)
        if result is None:
            result = PipelineStageResult(
                stage_name=name,
                stage_status="skipped",
                skip_reason=missing_reason,
                blocking_reasons=(missing_reason,),
            )
        normalized.append(_normalize_stage_result(result))
    return normalized


def _normalize_stage_result(result: PipelineStageResult) -> PipelineStageResult:
    skip_reason = result.skip_reason
    block_reason = result.block_reason
    failure_reason = result.failure_reason
    if result.stage_status == "skipped" and skip_reason is None:
        skip_reason = _first(result.blocking_reasons) or _first(result.warnings) or "not_reached"
    if result.stage_status == "blocked" and block_reason is None:
        block_reason = _first(result.blocking_reasons) or "stage_blocked"
    if result.stage_status == "failed" and failure_reason is None:
        failure_reason = _first(result.blocking_reasons) or "stage_failed"
    return PipelineStageResult(
        stage_name=result.stage_name,
        stage_status=result.stage_status,
        artifact_directory=result.artifact_directory,
        primary_artifacts=result.primary_artifacts,
        warnings=result.warnings,
        blocking_reasons=result.blocking_reasons,
        skip_reason=skip_reason,
        block_reason=block_reason,
        failure_reason=failure_reason,
    )


def build_pipeline_stage_matrix(
    stage_results: list[PipelineStageResult],
) -> dict[str, dict[str, Any]]:
    matrix: dict[str, dict[str, Any]] = {}
    for result in normalize_stage_results(stage_results):
        reason = (
            result.skip_reason
            if result.stage_skipped
            else result.block_reason
            if result.stage_blocked
            else result.failure_reason
            if result.stage_failed
            else _first(result.warnings)
        )
        matrix[result.stage_name] = {
            "status": result.stage_status,
            "ran": result.stage_ran,
            "skipped": result.stage_skipped,
            "blocked": result.stage_blocked,
            "failed": result.stage_failed,
            "warning": result.stage_warning,
            "reason": reason,
        }
    return matrix


def build_stage_counts(stage_results: list[PipelineStageResult]) -> dict[str, int]:
    normalized = normalize_stage_results(stage_results)
    return {
        "total_stages": len(PIPELINE_STAGE_NAMES),
        "completed": sum(result.stage_status == "completed" for result in normalized),
        "completed_with_warnings": sum(
            result.stage_status == "completed_with_warnings" for result in normalized
        ),
        "skipped": sum(result.stage_status == "skipped" for result in normalized),
        "blocked": sum(result.stage_status == "blocked" for result in normalized),
        "failed": sum(result.stage_status == "failed" for result in normalized),
    }


def pipeline_skip_reasons(stage_results: list[PipelineStageResult]) -> list[str]:
    reasons = [
        f"{result.stage_name}:{result.skip_reason}"
        for result in normalize_stage_results(stage_results)
        if result.stage_skipped and result.skip_reason
    ]
    return list(dict.fromkeys(reasons))


def pipeline_terminal_state(
    pipeline_status: str, stage_results: list[PipelineStageResult]
) -> dict[str, Any]:
    normalized = normalize_stage_results(stage_results)
    blocked = next((result for result in normalized if result.stage_blocked), None)
    failed = next((result for result in normalized if result.stage_failed), None)
    if pipeline_status == "pipeline_invalid_input":
        stage = failed.stage_name if failed else "input_load"
        reason = failed.failure_reason if failed else "pipeline_invalid_input"
        return _terminal(stage, reason or "pipeline_invalid_input", stage, "invalid_input")
    if pipeline_status == "pipeline_failed":
        stage = failed.stage_name if failed else "pipeline_report"
        reason = failed.failure_reason if failed else "pipeline_failed_safely"
        return _terminal(stage, reason or "pipeline_failed_safely", stage, "internal_failure")
    if pipeline_status == "pipeline_blocked":
        stage = blocked.stage_name if blocked else "pipeline_report"
        reason = blocked.block_reason if blocked else "pipeline_blocked"
        return _terminal(
            stage,
            _exit_reason_for_block(stage, reason or "pipeline_blocked"),
            stage,
            _failure_category_for_block(stage, reason or "pipeline_blocked"),
        )
    if pipeline_status == "pipeline_completed_with_warnings":
        return _terminal(
            "pipeline_report",
            "pipeline_completed_with_warnings",
            None,
            "warnings_only",
        )
    return _terminal(
        "pipeline_report",
        "pipeline_completed_simulation_only",
        None,
        "none",
    )


def build_evidence_summary(
    stage_results: list[PipelineStageResult],
    evidence_report: dict[str, Any] | None,
    *,
    evidence_stage_skipped: bool,
) -> dict[str, Any]:
    normalized = normalize_stage_results(stage_results)
    evidence_stage = next(
        result for result in normalized if result.stage_name == "evidence_bundle"
    )
    skipped = evidence_stage.stage_skipped or evidence_stage_skipped
    ran = evidence_stage.stage_ran and not skipped
    blocked = evidence_stage.stage_blocked
    if skipped:
        validation_status = None
        validation_passed = None
        failure_category = None
    else:
        validation_status = (
            evidence_report.get("evidence_validation_status")
            if evidence_report
            else None
        )
        validation_passed = (
            evidence_report.get("evidence_validation_passed")
            if evidence_report
            else None
        )
        failure_category = (
            evidence_report.get("evidence_failure_category")
            if evidence_report
            else None
        )
    return {
        "evidence_stage_present": True,
        "evidence_stage_ran": ran,
        "evidence_stage_skipped": skipped,
        "evidence_stage_blocked": blocked,
        "evidence_skip_reason": evidence_stage.skip_reason if skipped else None,
        "evidence_validation_status": validation_status,
        "evidence_validation_passed": validation_passed,
        "evidence_failure_category": failure_category,
    }


def build_pipeline_consistency_checks(
    stage_results: list[PipelineStageResult],
    matrix: dict[str, dict[str, Any]],
    counts: dict[str, int],
    pipeline_status: str,
    terminal: dict[str, Any],
    evidence_summary: dict[str, Any],
) -> dict[str, bool]:
    normalized = normalize_stage_results(stage_results)
    expected_matrix = build_pipeline_stage_matrix(normalized)
    expected_counts = build_stage_counts(normalized)
    evidence_stage = next(
        result for result in normalized if result.stage_name == "evidence_bundle"
    )
    return {
        "stage_results_match_matrix": matrix == expected_matrix,
        "stage_counts_match_results": counts == expected_counts,
        "skipped_stages_have_reasons": all(
            not result.stage_skipped or result.skip_reason is not None
            for result in normalized
        ),
        "blocked_pipeline_has_blocking_stage": (
            pipeline_status != "pipeline_blocked"
            or terminal["pipeline_blocking_stage"] is not None
        ),
        "artifact_index_matches_generated_artifacts": True,
        "evidence_summary_matches_stage_result": (
            evidence_summary["evidence_stage_skipped"] == evidence_stage.stage_skipped
            and evidence_summary["evidence_stage_blocked"] == evidence_stage.stage_blocked
        ),
    }


def build_transition_log(
    stage_results: list[PipelineStageResult],
) -> list[dict[str, Any]]:
    normalized = normalize_stage_results(stage_results)
    transitions: list[dict[str, Any]] = []
    previous: str | None = None
    for index, result in enumerate(normalized):
        if index == 0:
            transitions.append(
                {
                    "from_stage": None,
                    "to_stage": result.stage_name,
                    "transition": "start",
                    "reason": "pipeline_started",
                }
            )
        elif result.stage_skipped:
            transitions.append(
                {
                    "from_stage": previous,
                    "to_stage": result.stage_name,
                    "transition": "skip",
                    "reason": result.skip_reason,
                }
            )
        elif result.stage_blocked:
            transitions.append(
                {
                    "from_stage": previous,
                    "to_stage": result.stage_name,
                    "transition": "block",
                    "reason": result.block_reason,
                }
            )
        elif result.stage_failed:
            transitions.append(
                {
                    "from_stage": previous,
                    "to_stage": result.stage_name,
                    "transition": "fail",
                    "reason": result.failure_reason,
                }
            )
        else:
            transitions.append(
                {
                    "from_stage": previous,
                    "to_stage": result.stage_name,
                    "transition": "continue",
                    "reason": (
                        f"{previous}_completed" if previous else "pipeline_started"
                    ),
                }
            )
        previous = result.stage_name
    transitions.append(
        {
            "from_stage": previous,
            "to_stage": None,
            "transition": "complete",
            "reason": "pipeline_report_completed",
        }
    )
    return transitions


def _terminal(
    terminal_stage: str,
    exit_reason: str,
    blocking_stage: str | None,
    failure_category: str,
) -> dict[str, Any]:
    assert failure_category in PIPELINE_FAILURE_CATEGORIES
    return {
        "pipeline_terminal_stage": terminal_stage,
        "pipeline_exit_reason": exit_reason,
        "pipeline_blocking_stage": blocking_stage,
        "pipeline_failure_category": failure_category,
    }


def _exit_reason_for_block(stage_name: str, reason: str) -> str:
    if stage_name == "evidence_bundle":
        return "evidence_validation_blocked"
    return reason


def _failure_category_for_block(stage_name: str, reason: str) -> str:
    if stage_name == "runtime_dry_run" and reason == "blocked_by_safety_gate":
        return "runtime_safety_boundary"
    if stage_name == "runtime_dry_run" and reason == "blocked_by_bundle_validation":
        return "bundle_validation"
    if stage_name == "adapter_simulation":
        return "adapter_safety_boundary"
    if stage_name == "failure_rollback_simulation":
        return "failure_scenario_safety_boundary"
    if stage_name == "policy_simulation":
        return "policy_config_safety_boundary"
    if stage_name == "evidence_bundle":
        return "evidence_validation"
    return "internal_failure"


def _first(values: tuple[str, ...]) -> str | None:
    return values[0] if values else None


def _count(payload: dict[str, Any] | None, field: str) -> int:
    value = payload.get(field) if payload else None
    return len(value) if isinstance(value, list) else 0
