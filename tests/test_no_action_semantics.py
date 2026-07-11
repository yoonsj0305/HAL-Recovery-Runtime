from hal_runtime.rollback_simulator import simulate_failure_file


def test_no_action_cases_never_create_revert_actions(tmp_path):
    cases = [
        (
            "samples/runtime_plan_two_actions.json",
            "samples/failure_scenario_forced_safety_boundary_failure.json",
        ),
        ("samples/runtime_plan_blocked_by_safety_gate.json", None),
        (
            "samples/runtime_plan_valid.json",
            "samples/failure_scenario_unsafe_hardware_enabled.json",
        ),
        ("samples/runtime_plan_unsafe_hardware_enabled.json", None),
    ]
    for index, (plan_path, scenario_path) in enumerate(cases):
        outcome = simulate_failure_file(plan_path, tmp_path / str(index), scenario_path)
        plan = outcome.rollback_plan.to_dict()
        report = outcome.rollback_report.to_dict()
        assert plan["no_action_taken"] is True
        assert report["no_action_taken"] is True
        assert plan["simulated_revert_actions_planned"] == 0

