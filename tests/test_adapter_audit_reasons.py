from hal_runtime.adapter_simulator import load_runtime_plan, simulate_plan


def _report(sample):
    return simulate_plan(load_runtime_plan(sample)).report.to_dict()


def test_unsupported_action_populates_top_level_block_reason():
    report = _report("samples/runtime_plan_with_unknown_action.json")

    assert report["adapter_block_reasons"] == ["unsupported_action_type"]
    assert report["adapter_result_summary"]["blocked_unsupported_action"] == 1


def test_unsafe_hardware_populates_safety_failure_reason():
    report = _report("samples/runtime_plan_unsafe_hardware_enabled.json")

    assert report["adapter_block_reasons"] == ["safety_boundary_failed"]
    assert report["adapter_safety_failure_reasons"] == [
        "hardware_control_enabled_must_be_false"
    ]
    assert report["adapter_validation_reasons"] == []


def test_invalid_plan_populates_validation_reason_only():
    report = _report("samples/runtime_plan_missing_plan_status.json")

    assert report["adapter_validation_reasons"] == [
        "missing_required_field:plan_status"
    ]
    assert report["adapter_safety_failure_reasons"] == []


def test_missing_role_is_blocked_without_guessing_adapter():
    report = _report("samples/runtime_plan_role_missing.json")

    assert report["adapter_simulation_status"] == "adapter_simulation_completed_with_blocks"
    assert report["adapter_block_reasons"] == ["role_missing_or_unresolvable"]
    assert report["adapter_results"][0]["adapter_id"] == "unresolved_mock_adapter"
    assert report["adapter_results"][0]["simulation_status"] == "blocked_unsupported_role"
    assert report["adapter_result_summary"]["blocked_unsupported_role"] == 1


def test_skipped_plan_uses_plan_status_as_block_reason():
    report = _report("samples/runtime_plan_degraded_no_execution_plan.json")

    assert report["adapter_block_reasons"] == ["degraded_no_execution_plan"]
    assert report["adapter_execution_stage"] == "plan_executable_check"

