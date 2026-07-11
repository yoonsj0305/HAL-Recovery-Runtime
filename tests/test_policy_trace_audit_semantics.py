import json

from hal_runtime.adapter_simulator import simulate_plan_file
from hal_runtime.cli import EXIT_INVALID, main
from hal_runtime.policy_simulator import simulate_policy_file
from hal_runtime.rollback_simulator import simulate_failure_file


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_default_trace_contains_audit_lifecycle(tmp_path):
    simulate_policy_file("samples/runtime_plan_valid.json", tmp_path)
    kinds = {event["event_type"] for event in _events(tmp_path / "policy_trace.jsonl")}
    assert {"policy_input_summary_built", "policy_precedence_evaluated", "policy_decision_path_recorded"} <= kinds


def test_conflict_trace_identifies_combined_rollback_rule(tmp_path):
    rollback = tmp_path / "rollback"
    simulate_failure_file(
        "samples/runtime_plan_two_actions.json", rollback,
        "samples/failure_scenario_adapter_unavailable_after_first_action.json",
    )
    policy = tmp_path / "policy"
    simulate_policy_file(
        "samples/runtime_plan_two_actions.json", policy,
        rollback_report_path=rollback / "rollback_report.json",
    )
    events = _events(policy / "policy_trace.jsonl")
    assert any(event["event_type"] == "policy_conflict_detected" for event in events)
    precedence = next(event for event in events if event["event_type"] == "policy_precedence_evaluated")
    assert precedence["first_matched_rule"] == "rollback_required_with_safe_stop"


def test_unsafe_config_trace_identifies_blocking_input(tmp_path):
    assert main([
        "simulate-policy", "samples/runtime_plan_valid.json",
        "--policy-config", "samples/policy_config_unsafe_allow_real_execution.json",
        "--out", str(tmp_path),
    ]) == EXIT_INVALID
    events = _events(tmp_path / "policy_trace.jsonl")
    blocking = [event["input"] for event in events if event["event_type"] == "policy_blocking_input_detected"]
    assert "policy_config.allow_real_execution" in blocking


def test_adapter_warning_trace_identifies_warning_inputs(tmp_path):
    adapter = tmp_path / "adapter"
    simulate_plan_file("samples/runtime_plan_with_unknown_action.json", adapter)
    policy = tmp_path / "policy"
    simulate_policy_file(
        "samples/runtime_plan_with_unknown_action.json", policy,
        adapter_report_path=adapter / "adapter_report.json",
    )
    events = _events(policy / "policy_trace.jsonl")
    warnings = [event["input"] for event in events if event["event_type"] == "policy_warning_input_detected"]
    assert "adapter_report.blocked_actions" in warnings
