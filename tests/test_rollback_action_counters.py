from hal_runtime.rollback_simulator import simulate_failure_file


def _plan(tmp_path, scenario):
    return simulate_failure_file(
        "samples/runtime_plan_two_actions.json", tmp_path, scenario
    ).rollback_plan.to_dict()


def test_mixed_plan_counters_and_semantics_are_consistent(tmp_path):
    plan = _plan(
        tmp_path,
        "samples/failure_scenario_adapter_unavailable_after_first_action.json",
    )
    assert plan["simulated_revert_actions_planned"] == 1
    assert plan["safe_stop_markers_planned"] == 1
    assert plan["skip_markers_planned"] == 0
    assert plan["no_action_markers_planned"] == 0
    assert plan["rollback_required"] is True
    assert plan["safe_stop_required"] is True
    assert len(plan["rollback_actions"]) == 2


def test_safe_stop_marker_does_not_set_rollback_required(tmp_path):
    outcome = simulate_failure_file(
        "samples/runtime_plan_valid.json",
        tmp_path,
        "samples/failure_scenario_adapter_unavailable.json",
    )
    plan = outcome.rollback_plan.to_dict()
    report = outcome.rollback_report.to_dict()
    assert plan["safe_stop_markers_planned"] == 1
    assert plan["simulated_revert_actions_planned"] == 0
    assert plan["rollback_required"] is False
    assert report["rollback_actions_planned"] == 1


def test_no_action_counters_are_zero(tmp_path):
    plan = simulate_failure_file(
        "samples/runtime_plan_two_actions.json",
        tmp_path,
        "samples/failure_scenario_forced_safety_boundary_failure.json",
    ).rollback_plan.to_dict()
    assert plan["no_action_taken"] is True
    assert plan["simulated_revert_actions_planned"] == 0
    assert plan["safe_stop_markers_planned"] == 0
    assert plan["skip_markers_planned"] == 0

