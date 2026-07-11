from hal_runtime.rollback_simulator import simulate_failure_file


def test_timeout_before_action_is_safe_stop_only(tmp_path):
    outcome = simulate_failure_file(
        "samples/runtime_plan_valid.json",
        tmp_path,
        "samples/failure_scenario_action_timeout.json",
    )
    report = outcome.rollback_report.to_dict()
    assert report["rollback_required"] is False
    assert report["safe_stop_required"] is True
    assert report["safe_stop_markers_planned"] == 1
    assert "retry_not_allowed_in_v0_4_1" in report["failure_reasons"]


def test_adapter_failure_after_prior_action_requires_revert_and_safe_stop(tmp_path):
    plan = simulate_failure_file(
        "samples/runtime_plan_two_actions.json",
        tmp_path,
        "samples/failure_scenario_adapter_unavailable_after_first_action.json",
    ).rollback_plan.to_dict()
    assert plan["rollback_plan_status"] == "planned_simulation_with_safe_stop"
    assert plan["rollback_required"] is True
    assert plan["safe_stop_required"] is True
    assert {action["rollback_action_type"] for action in plan["rollback_actions"]} == {
        "simulated_revert",
        "safe_stop_marker",
    }


def test_safe_stop_marker_is_not_counted_as_revert(tmp_path):
    plan = simulate_failure_file(
        "samples/runtime_plan_valid.json",
        tmp_path,
        "samples/failure_scenario_adapter_unavailable.json",
    ).rollback_plan.to_dict()
    assert plan["safe_stop_markers_planned"] == 1
    assert plan["simulated_revert_actions_planned"] == 0

