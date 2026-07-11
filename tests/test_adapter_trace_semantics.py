from hal_runtime.adapter_simulator import load_runtime_plan, simulate_plan


def _event_types(sample):
    return [
        event["event_type"]
        for event in simulate_plan(load_runtime_plan(sample)).trace_events
    ]


def test_valid_trace_contains_each_audit_stage():
    event_types = _event_types("samples/runtime_plan_valid.json")

    assert event_types == [
        "plan_loaded",
        "plan_validation_passed",
        "adapter_safety_boundary_passed",
        "plan_executable_check_passed",
        "adapter_simulation_started",
        "adapter_resolved",
        "action_simulated",
        "adapter_simulation_completed",
    ]


def test_unsafe_trace_records_boundary_failure_and_block():
    event_types = _event_types("samples/runtime_plan_unsafe_hardware_enabled.json")

    assert "adapter_safety_boundary_failed" in event_types
    assert event_types[-1] == "adapter_simulation_blocked"


def test_invalid_trace_records_validation_failure_and_block():
    event_types = _event_types("samples/runtime_plan_missing_plan_status.json")

    assert "plan_validation_failed" in event_types
    assert event_types[-1] == "adapter_simulation_blocked"


def test_skipped_trace_records_executable_check_and_skip():
    event_types = _event_types("samples/runtime_plan_blocked_by_safety_gate.json")

    assert "plan_executable_check_failed" in event_types
    assert event_types[-1] == "adapter_simulation_skipped"


def test_unsupported_action_trace_separates_resolution_and_action_block():
    event_types = _event_types("samples/runtime_plan_with_unknown_action.json")

    assert "adapter_resolution_failed" in event_types
    assert "action_blocked" in event_types

