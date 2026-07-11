import json

from hal_runtime.rollback_simulator import simulate_failure_file


def _types(path):
    return [
        json.loads(line)["event_type"]
        for line in (path / "failure_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_safe_stop_trace_has_distinct_stage_events(tmp_path):
    simulate_failure_file(
        "samples/runtime_plan_valid.json",
        tmp_path,
        "samples/failure_scenario_adapter_unavailable.json",
    )
    types = _types(tmp_path)
    assert "safe_stop_planning_started" in types
    assert "safe_stop_plan_completed" in types


def test_revert_trace_has_rollback_stage_events(tmp_path):
    simulate_failure_file(
        "samples/runtime_plan_two_actions.json",
        tmp_path,
        "samples/failure_scenario_partial_plan_failure.json",
    )
    types = _types(tmp_path)
    assert "rollback_planning_started" in types
    assert "rollback_plan_completed" in types


def test_no_action_and_non_executable_traces_are_explicit(tmp_path):
    simulate_failure_file(
        "samples/runtime_plan_two_actions.json",
        tmp_path / "forced",
        "samples/failure_scenario_forced_safety_boundary_failure.json",
    )
    simulate_failure_file(
        "samples/runtime_plan_blocked_by_safety_gate.json", tmp_path / "blocked"
    )
    assert "no_action_taken" in _types(tmp_path / "forced")
    assert "source_plan_not_executable" in _types(tmp_path / "blocked")
    assert "no_action_taken" in _types(tmp_path / "blocked")


def test_unsafe_scenario_trace_has_boundary_and_no_action(tmp_path):
    simulate_failure_file(
        "samples/runtime_plan_valid.json",
        tmp_path,
        "samples/failure_scenario_unsafe_hardware_enabled.json",
    )
    types = _types(tmp_path)
    assert "scenario_safety_boundary_failed" in types
    assert "no_action_taken" in types

