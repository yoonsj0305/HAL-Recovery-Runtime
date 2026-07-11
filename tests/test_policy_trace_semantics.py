import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_default_trace_has_complete_decision_sequence(tmp_path):
    assert main(["simulate-policy", "samples/runtime_plan_valid.json", "--out", str(tmp_path)]) == EXIT_OK
    kinds = {event["event_type"] for event in _events(tmp_path / "policy_trace.jsonl")}
    assert {"policy_simulation_started", "runtime_plan_loaded", "policy_evaluation_started", "policy_decision_selected", "policy_simulation_completed"} <= kinds


def test_blocked_traces_record_failure_kind(tmp_path):
    unsafe = tmp_path / "unsafe"
    invalid = tmp_path / "invalid"
    assert main(["simulate-policy", "samples/runtime_plan_valid.json", "--policy-config", "samples/policy_config_unsafe_retry.json", "--out", str(unsafe)]) == EXIT_INVALID
    assert "policy_safety_boundary_failed" in {e["event_type"] for e in _events(unsafe / "policy_trace.jsonl")}
    assert main(["simulate-policy", "samples/runtime_plan_missing_plan_status.json", "--out", str(invalid)]) == EXIT_INVALID
    assert "policy_input_validation_failed" in {e["event_type"] for e in _events(invalid / "policy_trace.jsonl")}


def test_rollback_and_safe_stop_detection_events(tmp_path):
    failure = tmp_path / "failure"
    policy = tmp_path / "policy"
    main(["simulate-failure", "samples/runtime_plan_two_actions.json", "--scenario", "samples/failure_scenario_adapter_unavailable_after_first_action.json", "--out", str(failure)])
    main(["simulate-policy", "samples/runtime_plan_two_actions.json", "--rollback-report", str(failure / "rollback_report.json"), "--out", str(policy)])
    kinds = {event["event_type"] for event in _events(policy / "policy_trace.jsonl")}
    assert "rollback_required_detected" in kinds
    assert "safe_stop_required_detected" in kinds
