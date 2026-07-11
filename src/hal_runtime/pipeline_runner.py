"""Simulation-only end-to-end pipeline orchestration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .adapter_simulator import simulate_plan_file
from .bundle_loader import ARTIFACT_NAMES, load_compiler_bundle
from .dry_run_executor import run_bundle_dry_run, run_dry_run
from .event_log import write_json
from .evidence_bundle_builder import build_evidence_bundle
from .evidence_collector import EvidenceCollectionError
from .evidence_schema import ARTIFACT_TYPES
from .pipeline_artifacts import build_pipeline_artifact_index
from .pipeline_models import PIPELINE_ID, PipelineRunResult, PipelineStageResult
from .pipeline_report import (
    build_pipeline_report,
    build_pipeline_summary,
    pipeline_terminal_state,
)
from .pipeline_stages import PIPELINE_STAGE_NAMES
from .pipeline_trace import (
    consistency_checked_event,
    pipeline_completed_event,
    pipeline_started_event,
    stage_completed_event,
    stage_failed_event,
    stage_skipped_event,
    stage_started_event,
    stage_warning_event,
    terminal_state_event,
    write_pipeline_trace,
)
from .policy_simulator import simulate_policy_file
from .profile_loader import load_profile
from .rollback_simulator import simulate_failure_file


EXIT_OK = 0
EXIT_INVALID = 2
POLICY_BLOCK_STATUSES = {
    "invalid_policy_input",
    "blocked_by_safety_boundary",
    "blocked_invalid_artifacts",
    "blocked_policy_config_safety_boundary",
}


def run_pipeline(
    *,
    output_dir: str | Path,
    profile_path: str | Path | None = None,
    bundle_path: str | Path | None = None,
    failure_scenario_path: str | Path | None = None,
    policy_config_path: str | Path | None = None,
    stop_on_warning: bool = False,
    no_evidence: bool = False,
) -> PipelineRunResult:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    input_mode = (
        "profile"
        if profile_path is not None and bundle_path is None
        else "bundle" if bundle_path is not None and profile_path is None else "invalid"
    )
    trace: list[dict[str, Any]] = [pipeline_started_event(input_mode)]
    stages: list[PipelineStageResult] = []
    warnings: list[str] = []
    blocking: list[str] = []
    runtime_plan: dict[str, Any] | None = None
    runtime_report: dict[str, Any] | None = None
    adapter_report: dict[str, Any] | None = None
    rollback_report: dict[str, Any] | None = None
    policy_report: dict[str, Any] | None = None
    evidence_report: dict[str, Any] | None = None
    profile_id: str | None = None
    evidence_stage_skipped = no_evidence

    input_error = _validate_inputs(
        profile_path=profile_path,
        bundle_path=bundle_path,
        failure_scenario_path=failure_scenario_path,
        policy_config_path=policy_config_path,
        output=output,
    )
    if input_error:
        stages.append(_stage("input_load", "failed", blocking_reasons=(input_error,)))
        trace.extend(
            (
                stage_failed_event("input_load", "failed", input_error),
                pipeline_completed_event("pipeline_invalid_input"),
            )
        )
        return _finalize(
            output=output,
            input_mode=input_mode,
            profile_id=None,
            pipeline_status="pipeline_invalid_input",
            exit_code=EXIT_INVALID,
            stages=stages,
            trace=trace,
            runtime_plan=None,
            runtime_report=None,
            adapter_report=None,
            rollback_report=None,
            policy_report=None,
            evidence_report=None,
            warnings=warnings,
            blocking=[input_error],
            evidence_stage_skipped=evidence_stage_skipped,
        )

    trace.append(stage_started_event("input_load"))
    try:
        if profile_path is not None:
            profile = load_profile(profile_path)
            profile_id = _string_or_none(profile.get("profile_id"))
        else:
            bundle = load_compiler_bundle(bundle_path)
            profile_id = (
                _string_or_none(bundle.recovery_profile.get("profile_id"))
                if bundle.recovery_profile
                else None
            )
    except Exception as exc:
        reason = f"input_load_failed:{exc}"
        stages.append(_stage("input_load", "failed", blocking_reasons=(reason,)))
        trace.extend(
            (
                stage_failed_event("input_load", "failed", reason),
                pipeline_completed_event("pipeline_invalid_input"),
            )
        )
        return _finalize(
            output=output,
            input_mode=input_mode,
            profile_id=None,
            pipeline_status="pipeline_invalid_input",
            exit_code=EXIT_INVALID,
            stages=stages,
            trace=trace,
            runtime_plan=None,
            runtime_report=None,
            adapter_report=None,
            rollback_report=None,
            policy_report=None,
            evidence_report=None,
            warnings=warnings,
            blocking=[reason],
            evidence_stage_skipped=evidence_stage_skipped,
        )
    stages.append(_stage("input_load", "completed"))
    trace.append(stage_completed_event("input_load"))

    runtime_dir = output / "runtime"
    trace.append(stage_started_event("runtime_dry_run"))
    try:
        if profile_path is not None:
            dry_run = run_dry_run(profile_path, runtime_dir)
        else:
            dry_run = run_bundle_dry_run(bundle_path, runtime_dir)
    except Exception as exc:
        reason = f"runtime_dry_run_failed:{exc}"
        stages.append(_stage("runtime_dry_run", "failed", "runtime", ("runtime_report.json",), (), (reason,)))
        trace.extend((stage_failed_event("runtime_dry_run", "failed", reason),))
        blocking.append(reason)
        return _blocked_after(
            output, input_mode, profile_id, stages, trace, runtime_plan, runtime_report,
            adapter_report, rollback_report, policy_report, evidence_report, warnings,
            blocking, evidence_stage_skipped,
        )
    runtime_plan = dry_run.plan.to_dict()
    runtime_report = dry_run.report.to_dict()
    profile_id = profile_id or _string_or_none(runtime_plan.get("profile_id"))
    runtime_warnings = _runtime_warnings(runtime_report)
    if runtime_warnings:
        warnings.extend(runtime_warnings)
        for reason in runtime_warnings:
            trace.append(stage_warning_event("runtime_dry_run", reason))
    if _runtime_blocked(runtime_report):
        reason = _runtime_block_reason(runtime_report, runtime_plan)
        stages.append(
            _stage(
                "runtime_dry_run",
                "blocked",
                "runtime",
                ("runtime_plan.json", "runtime_report.json"),
                tuple(runtime_warnings),
                (reason,),
            )
        )
        blocking.append(reason)
        trace.append(stage_failed_event("runtime_dry_run", "blocked", reason))
        _skip_dependent_stages(stages, trace, "runtime_dry_run_blocked")
        return _blocked_after(
            output, input_mode, profile_id, stages, trace, runtime_plan, runtime_report,
            adapter_report, rollback_report, policy_report, evidence_report, warnings,
            blocking, evidence_stage_skipped,
        )
    runtime_stage_status = "completed_with_warnings" if runtime_warnings else "completed"
    stages.append(
        _stage(
            "runtime_dry_run",
            runtime_stage_status,
            "runtime",
            ("runtime_plan.json", "runtime_report.json"),
            tuple(runtime_warnings),
        )
    )
    trace.append(stage_completed_event("runtime_dry_run"))
    if stop_on_warning and runtime_warnings:
        _skip_remaining_after_warning(stages, trace, "runtime_dry_run_warning")
        return _completed_with_warnings_after(
            output, input_mode, profile_id, stages, trace, runtime_plan, runtime_report,
            adapter_report, rollback_report, policy_report, evidence_report, warnings,
            evidence_stage_skipped,
        )

    adapter_dir = output / "adapter"
    trace.append(stage_started_event("adapter_simulation"))
    adapter = simulate_plan_file(runtime_dir / "runtime_plan.json", adapter_dir)
    adapter_report = adapter.report.to_dict()
    if adapter_report.get("adapter_simulation_status") in {
        "invalid_plan",
        "blocked_safety_boundary",
    }:
        reason = str(adapter_report.get("adapter_simulation_status"))
        stages.append(
            _stage(
                "adapter_simulation",
                "blocked",
                "adapter",
                ("adapter_report.json", "adapter_trace.jsonl"),
                (),
                (reason,),
            )
        )
        blocking.append(reason)
        trace.append(stage_failed_event("adapter_simulation", "blocked", reason))
    else:
        adapter_warnings = list(adapter_report.get("adapter_block_reasons", []))
        if adapter_warnings:
            warnings.extend(adapter_warnings)
            for reason in adapter_warnings:
                trace.append(stage_warning_event("adapter_simulation", reason))
        stages.append(
            _stage(
                "adapter_simulation",
                "completed_with_warnings" if adapter_warnings else "completed",
                "adapter",
                ("adapter_report.json", "adapter_trace.jsonl"),
                tuple(adapter_warnings),
            )
        )
        trace.append(stage_completed_event("adapter_simulation"))
        if stop_on_warning and adapter_warnings:
            _skip_remaining_after_warning(stages, trace, "adapter_simulation_warning")
            return _completed_with_warnings_after(
                output, input_mode, profile_id, stages, trace, runtime_plan,
                runtime_report, adapter_report, rollback_report, policy_report,
                evidence_report, warnings, evidence_stage_skipped,
            )

    failure_dir = output / "failure"
    trace.append(stage_started_event("failure_rollback_simulation"))
    failure = simulate_failure_file(
        runtime_dir / "runtime_plan.json",
        failure_dir,
        failure_scenario_path,
    )
    rollback_report = failure.rollback_report.to_dict()
    if rollback_report.get("rollback_simulation_status") in {
        "invalid_plan",
        "blocked_scenario_safety_boundary",
        "blocked_plan_safety_boundary",
    }:
        reason = str(rollback_report.get("rollback_simulation_status"))
        stages.append(
            _stage(
                "failure_rollback_simulation",
                "blocked",
                "failure",
                ("failure_trace.jsonl", "rollback_plan.json", "rollback_report.json"),
                (),
                (reason,),
            )
        )
        blocking.append(reason)
        trace.append(stage_failed_event("failure_rollback_simulation", "blocked", reason))
        _skip_policy_evidence_stages(stages, trace, "failure_rollback_simulation_blocked")
        return _blocked_after(
            output, input_mode, profile_id, stages, trace, runtime_plan, runtime_report,
            adapter_report, rollback_report, policy_report, evidence_report, warnings,
            blocking, evidence_stage_skipped,
        )
    stages.append(
        _stage(
            "failure_rollback_simulation",
            "completed",
            "failure",
            ("failure_trace.jsonl", "rollback_plan.json", "rollback_report.json"),
        )
    )
    trace.append(stage_completed_event("failure_rollback_simulation"))

    policy_dir = output / "policy"
    trace.append(stage_started_event("policy_simulation"))
    policy = simulate_policy_file(
        runtime_dir / "runtime_plan.json",
        policy_dir,
        adapter_dir / "adapter_report.json",
        failure_dir / "rollback_report.json",
        policy_config_path,
    )
    policy_report = policy.report.to_dict()
    policy_status = str(policy_report.get("policy_status"))
    if policy_status in POLICY_BLOCK_STATUSES:
        reason = policy_status
        stages.append(
            _stage(
                "policy_simulation",
                "blocked",
                "policy",
                ("policy_trace.jsonl", "policy_decision.json", "policy_report.json"),
                (),
                (reason,),
            )
        )
        blocking.append(reason)
        trace.append(stage_failed_event("policy_simulation", "blocked", reason))
        _skip_evidence_stage(stages, trace, "policy_simulation_blocked")
        evidence_stage_skipped = True
        return _blocked_after(
            output, input_mode, profile_id, stages, trace, runtime_plan, runtime_report,
            adapter_report, rollback_report, policy_report, evidence_report, warnings,
            blocking, evidence_stage_skipped,
        )
    policy_warnings = list(policy_report.get("warning_reasons", [])) + list(
        policy_report.get("policy_warning_inputs", [])
    )
    if policy_warnings:
        warnings.extend(policy_warnings)
        for reason in policy_warnings:
            trace.append(stage_warning_event("policy_simulation", reason))
    stages.append(
        _stage(
            "policy_simulation",
            "completed_with_warnings" if policy_warnings else "completed",
            "policy",
            ("policy_trace.jsonl", "policy_decision.json", "policy_report.json"),
            tuple(policy_warnings),
        )
    )
    trace.append(stage_completed_event("policy_simulation"))
    if stop_on_warning and policy_warnings:
        _skip_evidence_stage(stages, trace, "stop_on_warning")
        evidence_stage_skipped = True
        return _completed_with_warnings_after(
            output, input_mode, profile_id, stages, trace, runtime_plan, runtime_report,
            adapter_report, rollback_report, policy_report, evidence_report, warnings,
            evidence_stage_skipped,
        )

    if no_evidence:
        stages.append(
            _stage(
                "evidence_bundle",
                "skipped",
                "evidence",
                skip_reason="evidence_disabled",
            )
        )
        trace.append(stage_skipped_event("evidence_bundle", "evidence_disabled"))
    else:
        evidence_dir = output / "evidence"
        trace.append(stage_started_event("evidence_bundle"))
        try:
            evidence = _build_pipeline_evidence(
                output,
                evidence_dir,
                profile_path=Path(profile_path) if profile_path is not None else None,
                bundle_path=Path(bundle_path) if bundle_path is not None else None,
            )
        except (EvidenceCollectionError, OSError) as exc:
            reason = f"evidence_bundle_failed:{exc}"
            stages.append(
                _stage(
                    "evidence_bundle",
                    "blocked",
                    "evidence",
                    ("evidence_manifest.json", "evidence_bundle.json", "evidence_report.json"),
                    (),
                    (reason,),
                )
            )
            blocking.append(reason)
            trace.append(stage_failed_event("evidence_bundle", "blocked", reason))
            return _blocked_after(
                output, input_mode, profile_id, stages, trace, runtime_plan,
                runtime_report, adapter_report, rollback_report, policy_report,
                evidence_report, warnings, blocking, evidence_stage_skipped,
            )
        evidence_report = evidence.report
        evidence_status = str(evidence_report.get("evidence_validation_status"))
        if not evidence_report.get("evidence_validation_passed", False):
            reason = evidence_status
            stages.append(
                _stage(
                    "evidence_bundle",
                    "blocked",
                    "evidence",
                    ("evidence_manifest.json", "evidence_bundle.json", "evidence_report.json"),
                    (),
                    (reason,),
                )
            )
            blocking.append(reason)
            trace.append(stage_failed_event("evidence_bundle", "blocked", reason))
            return _blocked_after(
                output, input_mode, profile_id, stages, trace, runtime_plan,
                runtime_report, adapter_report, rollback_report, policy_report,
                evidence_report, warnings, blocking, evidence_stage_skipped,
            )
        evidence_warnings = list(evidence_report.get("evidence_warning_reasons", []))
        if evidence_warnings:
            warnings.extend(evidence_warnings)
            for reason in evidence_warnings:
                trace.append(stage_warning_event("evidence_bundle", reason))
        stages.append(
            _stage(
                "evidence_bundle",
                "completed_with_warnings" if evidence_warnings else "completed",
                "evidence",
                ("evidence_manifest.json", "evidence_bundle.json", "evidence_report.json"),
                tuple(evidence_warnings),
            )
        )
        trace.append(stage_completed_event("evidence_bundle"))

    if blocking:
        pipeline_status = "pipeline_blocked"
        exit_code = EXIT_INVALID
    else:
        pipeline_status = (
            "pipeline_completed_with_warnings" if warnings else "pipeline_completed"
        )
        exit_code = EXIT_OK
    trace.append(stage_completed_event("pipeline_report"))
    trace.append(pipeline_completed_event(pipeline_status))
    stages.append(
        _stage(
        "pipeline_report",
        "completed" if blocking else "completed_with_warnings" if warnings else "completed",
            None,
            ("pipeline_summary.json", "pipeline_report.json", "pipeline_artifact_index.json"),
            tuple(warnings),
        )
    )
    return _finalize(
        output=output,
        input_mode=input_mode,
        profile_id=profile_id,
        pipeline_status=pipeline_status,
        exit_code=exit_code,
        stages=stages,
        trace=trace,
        runtime_plan=runtime_plan,
        runtime_report=runtime_report,
        adapter_report=adapter_report,
        rollback_report=rollback_report,
        policy_report=policy_report,
        evidence_report=evidence_report,
        warnings=warnings,
        blocking=blocking,
        evidence_stage_skipped=evidence_stage_skipped,
    )


def _validate_inputs(
    *,
    profile_path: str | Path | None,
    bundle_path: str | Path | None,
    failure_scenario_path: str | Path | None,
    policy_config_path: str | Path | None,
    output: Path,
) -> str | None:
    if (profile_path is None and bundle_path is None) or (
        profile_path is not None and bundle_path is not None
    ):
        return "exactly_one_of_profile_or_bundle_required"
    if profile_path is not None and not Path(profile_path).is_file():
        return "profile_path_must_be_file"
    if bundle_path is not None and not Path(bundle_path).is_dir():
        return "bundle_path_must_be_directory"
    if failure_scenario_path is not None and not Path(failure_scenario_path).is_file():
        return "failure_scenario_path_must_be_file"
    if policy_config_path is not None and not Path(policy_config_path).is_file():
        return "policy_config_path_must_be_file"
    input_root = Path(profile_path).parent if profile_path is not None else Path(bundle_path)
    try:
        resolved_output = output.resolve()
        resolved_input = input_root.resolve()
    except OSError:
        return "path_resolution_failed"
    if resolved_output == resolved_input or resolved_input in resolved_output.parents:
        return "output_directory_must_not_be_inside_input_directory"
    return None


def _stage(
    stage_name: str,
    stage_status: str,
    artifact_directory: str | None = None,
    primary_artifacts: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
    blocking_reasons: tuple[str, ...] = (),
    skip_reason: str | None = None,
    block_reason: str | None = None,
    failure_reason: str | None = None,
) -> PipelineStageResult:
    if stage_status == "skipped" and skip_reason is None:
        skip_reason = (
            blocking_reasons[0]
            if blocking_reasons
            else warnings[0] if warnings else "not_reached"
        )
    if stage_status == "blocked" and block_reason is None:
        block_reason = blocking_reasons[0] if blocking_reasons else "stage_blocked"
    if stage_status == "failed" and failure_reason is None:
        failure_reason = blocking_reasons[0] if blocking_reasons else "stage_failed"
    return PipelineStageResult(
        stage_name=stage_name,
        stage_status=stage_status,
        artifact_directory=artifact_directory,
        primary_artifacts=primary_artifacts,
        warnings=warnings,
        blocking_reasons=blocking_reasons,
        skip_reason=skip_reason,
        block_reason=block_reason,
        failure_reason=failure_reason,
    )


def _runtime_blocked(
    runtime_report: dict[str, Any],
) -> bool:
    return (
        runtime_report.get("safety_gate_passed") is False
        or runtime_report.get("bundle_validation_passed") is False
    )


def _runtime_block_reason(
    runtime_report: dict[str, Any], runtime_plan: dict[str, Any]
) -> str:
    if runtime_report.get("bundle_validation_passed") is False:
        return "blocked_by_bundle_validation"
    if runtime_report.get("safety_gate_passed") is False:
        return "blocked_by_safety_gate"
    reasons = runtime_plan.get("plan_block_reasons")
    return str(reasons[0]) if isinstance(reasons, list) and reasons else "runtime_blocked"


def _runtime_warnings(runtime_report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for field in ("bundle_validation_warnings", "degraded_mode_reasons"):
        value = runtime_report.get(field)
        if isinstance(value, list):
            warnings.extend(str(item) for item in value)
    if runtime_report.get("degraded_bundle_mode") is True:
        warnings.append("degraded_bundle_mode")
    return list(dict.fromkeys(warnings))


def _skip_dependent_stages(
    stages: list[PipelineStageResult], trace: list[dict[str, Any]], reason: str
) -> None:
    for name in (
        "adapter_simulation",
        "failure_rollback_simulation",
        "policy_simulation",
        "evidence_bundle",
    ):
        stages.append(_stage(name, "skipped", blocking_reasons=(reason,)))
        trace.append(stage_skipped_event(name, reason))


def _skip_policy_evidence_stages(
    stages: list[PipelineStageResult], trace: list[dict[str, Any]], reason: str
) -> None:
    for name in ("policy_simulation", "evidence_bundle"):
        stages.append(_stage(name, "skipped", blocking_reasons=(reason,)))
        trace.append(stage_skipped_event(name, reason))


def _skip_evidence_stage(
    stages: list[PipelineStageResult], trace: list[dict[str, Any]], reason: str
) -> None:
    stages.append(_stage("evidence_bundle", "skipped", blocking_reasons=(reason,)))
    trace.append(stage_skipped_event("evidence_bundle", reason))


def _skip_remaining_after_warning(
    stages: list[PipelineStageResult], trace: list[dict[str, Any]], reason: str
) -> None:
    present = {stage.stage_name for stage in stages}
    for name in PIPELINE_STAGE_NAMES:
        if name in present or name == "input_load" or name == "pipeline_report":
            continue
        stages.append(_stage(name, "skipped", skip_reason="stop_on_warning"))
        trace.append(stage_skipped_event(name, "stop_on_warning"))


def _blocked_after(
    output: Path,
    input_mode: str,
    profile_id: str | None,
    stages: list[PipelineStageResult],
    trace: list[dict[str, Any]],
    runtime_plan: dict[str, Any] | None,
    runtime_report: dict[str, Any] | None,
    adapter_report: dict[str, Any] | None,
    rollback_report: dict[str, Any] | None,
    policy_report: dict[str, Any] | None,
    evidence_report: dict[str, Any] | None,
    warnings: list[str],
    blocking: list[str],
    evidence_stage_skipped: bool,
) -> PipelineRunResult:
    trace.append(stage_completed_event("pipeline_report", "blocked"))
    trace.append(pipeline_completed_event("pipeline_blocked"))
    stages.append(
        _stage(
            "pipeline_report",
            "completed",
            None,
            ("pipeline_summary.json", "pipeline_report.json", "pipeline_artifact_index.json"),
        )
    )
    return _finalize(
        output=output,
        input_mode=input_mode,
        profile_id=profile_id,
        pipeline_status="pipeline_blocked",
        exit_code=EXIT_INVALID,
        stages=stages,
        trace=trace,
        runtime_plan=runtime_plan,
        runtime_report=runtime_report,
        adapter_report=adapter_report,
        rollback_report=rollback_report,
        policy_report=policy_report,
        evidence_report=evidence_report,
        warnings=warnings,
        blocking=blocking,
        evidence_stage_skipped=evidence_stage_skipped,
    )


def _completed_with_warnings_after(
    output: Path,
    input_mode: str,
    profile_id: str | None,
    stages: list[PipelineStageResult],
    trace: list[dict[str, Any]],
    runtime_plan: dict[str, Any] | None,
    runtime_report: dict[str, Any] | None,
    adapter_report: dict[str, Any] | None,
    rollback_report: dict[str, Any] | None,
    policy_report: dict[str, Any] | None,
    evidence_report: dict[str, Any] | None,
    warnings: list[str],
    evidence_stage_skipped: bool,
) -> PipelineRunResult:
    trace.append(stage_completed_event("pipeline_report", "warning"))
    trace.append(pipeline_completed_event("pipeline_completed_with_warnings"))
    stages.append(
        _stage(
            "pipeline_report",
            "completed_with_warnings",
            None,
            ("pipeline_summary.json", "pipeline_report.json", "pipeline_artifact_index.json"),
            tuple(warnings),
        )
    )
    return _finalize(
        output=output,
        input_mode=input_mode,
        profile_id=profile_id,
        pipeline_status="pipeline_completed_with_warnings",
        exit_code=EXIT_OK,
        stages=stages,
        trace=trace,
        runtime_plan=runtime_plan,
        runtime_report=runtime_report,
        adapter_report=adapter_report,
        rollback_report=rollback_report,
        policy_report=policy_report,
        evidence_report=evidence_report,
        warnings=warnings,
        blocking=[],
        evidence_stage_skipped=evidence_stage_skipped,
    )


def _finalize(
    *,
    output: Path,
    input_mode: str,
    profile_id: str | None,
    pipeline_status: str,
    exit_code: int,
    stages: list[PipelineStageResult],
    trace: list[dict[str, Any]],
    runtime_plan: dict[str, Any] | None,
    runtime_report: dict[str, Any] | None,
    adapter_report: dict[str, Any] | None,
    rollback_report: dict[str, Any] | None,
    policy_report: dict[str, Any] | None,
    evidence_report: dict[str, Any] | None,
    warnings: list[str],
    blocking: list[str],
    evidence_stage_skipped: bool,
) -> PipelineRunResult:
    terminal = pipeline_terminal_state(pipeline_status, stages)
    completion_event: dict[str, Any] | None = None
    if trace and trace[-1].get("event_type") == "pipeline_completed":
        completion_event = trace.pop()
    terminal_status = (
        "ok"
        if pipeline_status.startswith("pipeline_completed")
        else "blocked"
        if pipeline_status in {"pipeline_blocked", "pipeline_invalid_input"}
        else "failed"
    )
    trace.append(
        terminal_state_event(
            pipeline_terminal_stage=terminal["pipeline_terminal_stage"],
            pipeline_exit_reason=terminal["pipeline_exit_reason"],
            status=terminal_status,
        )
    )
    trace.append(consistency_checked_event())
    trace.append(completion_event or pipeline_completed_event(pipeline_status))
    pipeline_reasons = [_reason_for_status(pipeline_status)]
    summary = build_pipeline_summary(
        input_mode=input_mode,
        pipeline_status=pipeline_status,
        stage_results=stages,
        runtime_report=runtime_report,
        policy_report=policy_report,
        evidence_report=evidence_report,
        pipeline_warnings=warnings,
    )
    report = build_pipeline_report(
        input_mode=input_mode,
        profile_id=profile_id,
        pipeline_status=pipeline_status,
        pipeline_exit_code=exit_code,
        stage_results=stages,
        runtime_plan=runtime_plan,
        runtime_report=runtime_report,
        adapter_report=adapter_report,
        rollback_report=rollback_report,
        policy_report=policy_report,
        evidence_report=evidence_report,
        pipeline_reasons=pipeline_reasons,
        pipeline_warning_reasons=warnings,
        pipeline_blocking_reasons=blocking,
        evidence_stage_skipped=evidence_stage_skipped,
    )
    write_pipeline_trace(output / "pipeline_trace.jsonl", trace)
    write_json(output / "pipeline_summary.json", summary)
    write_json(output / "pipeline_report.json", report)
    artifact_index = build_pipeline_artifact_index(output)
    write_json(output / "pipeline_artifact_index.json", artifact_index)
    return PipelineRunResult(exit_code, summary, report, artifact_index, tuple(trace))


def _reason_for_status(pipeline_status: str) -> str:
    return {
        "pipeline_completed": "pipeline_completed_simulation_only",
        "pipeline_completed_with_warnings": "pipeline_completed_with_warnings_simulation_only",
        "pipeline_blocked": "pipeline_blocked_simulation_only",
        "pipeline_failed": "pipeline_failed_safely",
        "pipeline_invalid_input": "pipeline_invalid_input",
    }[pipeline_status]


def _build_pipeline_evidence(
    output: Path,
    evidence_dir: Path,
    *,
    profile_path: Path | None,
    bundle_path: Path | None,
):
    with TemporaryDirectory(prefix="hal_rr_pipeline_evidence_") as staging_name:
        staging = Path(staging_name)
        _copy_if_present(output / "runtime" / "runtime_plan.json", staging / "runtime_plan.json")
        _copy_if_present(output / "runtime" / "runtime_report.json", staging / "runtime_report.json")
        _copy_if_present(output / "runtime" / "runtime_events.jsonl", staging / "runtime_events.jsonl")
        _copy_if_present(output / "adapter" / "adapter_report.json", staging / "adapter_report.json")
        _copy_if_present(output / "adapter" / "adapter_trace.jsonl", staging / "adapter_trace.jsonl")
        _copy_if_present(output / "failure" / "failure_trace.jsonl", staging / "failure_trace.jsonl")
        _copy_if_present(output / "failure" / "rollback_plan.json", staging / "rollback_plan.json")
        _copy_if_present(output / "failure" / "rollback_report.json", staging / "rollback_report.json")
        _copy_if_present(output / "policy" / "policy_trace.jsonl", staging / "policy_trace.jsonl")
        _copy_if_present(output / "policy" / "policy_decision.json", staging / "policy_decision.json")
        _copy_if_present(output / "policy" / "policy_report.json", staging / "policy_report.json")
        if profile_path is not None:
            _copy_if_present(profile_path, staging / "recovery_profile.json")
        if bundle_path is not None:
            for name in ARTIFACT_NAMES:
                if name in ARTIFACT_TYPES:
                    _copy_if_present(bundle_path / name, staging / name)
        return build_evidence_bundle(staging, evidence_dir)


def _copy_if_present(source: Path, target: Path) -> None:
    if source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None
