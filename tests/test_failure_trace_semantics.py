import json

from hal_runtime.rollback_simulator import simulate_failure_file


def _types(path):
    return [json.loads(line)["event_type"] for line in path.read_text(encoding="utf-8").splitlines()]


def test_no_failure_trace_marks_rollback_not_required(tmp_path):
    simulate_failure_file("samples/runtime_plan_valid.json", tmp_path)
    assert "rollback_not_required" in _types(tmp_path / "failure_trace.jsonl")


def test_partial_trace_has_failure_and_rollback_action(tmp_path):
    simulate_failure_file(
        "samples/runtime_plan_two_actions.json", tmp_path,
        "samples/failure_scenario_partial_plan_failure.json",
    )
    types = _types(tmp_path / "failure_trace.jsonl")
    assert "failure_injected" in types
    assert "rollback_action_planned" in types


def test_unsafe_scenario_trace_records_boundary_failure(tmp_path):
    simulate_failure_file(
        "samples/runtime_plan_valid.json", tmp_path,
        "samples/failure_scenario_unsafe_hardware_enabled.json",
    )
    assert "scenario_safety_boundary_failed" in _types(tmp_path / "failure_trace.jsonl")


def test_invalid_plan_trace_records_block(tmp_path):
    simulate_failure_file("samples/runtime_plan_missing_plan_status.json", tmp_path)
    types = _types(tmp_path / "failure_trace.jsonl")
    assert "plan_validation_failed" in types
    assert "failure_simulation_blocked" in types

