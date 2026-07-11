from hal_runtime.rollback_simulator import simulate_failure_file


def _report(tmp_path, plan, scenario=None):
    return simulate_failure_file(plan, tmp_path, scenario).rollback_report


def test_no_failure_has_no_rollback_safe_stop_or_no_action(tmp_path):
    report = _report(tmp_path, "samples/runtime_plan_valid.json")
    assert report.rollback_required is False
    assert report.safe_stop_required is False
    assert report.no_action_taken is False


def test_partial_failure_requires_revert(tmp_path):
    report = _report(
        tmp_path,
        "samples/runtime_plan_two_actions.json",
        "samples/failure_scenario_partial_plan_failure.json",
    )
    assert report.rollback_required is True
    assert report.safe_stop_required is False


def test_route_failure_after_prior_action_requires_revert_only(tmp_path):
    report = _report(
        tmp_path,
        "samples/runtime_plan_two_actions.json",
        "samples/failure_scenario_route_unavailable_after_first_action.json",
    )
    assert report.rollback_required is True
    assert report.safe_stop_required is False


def test_adapter_unavailable_before_action_requires_safe_stop_only(tmp_path):
    report = _report(
        tmp_path,
        "samples/runtime_plan_valid.json",
        "samples/failure_scenario_adapter_unavailable.json",
    )
    assert report.rollback_required is False
    assert report.safe_stop_required is True


def test_forced_failure_and_non_executable_plan_take_no_action(tmp_path):
    forced = _report(
        tmp_path / "forced",
        "samples/runtime_plan_two_actions.json",
        "samples/failure_scenario_forced_safety_boundary_failure.json",
    )
    blocked = _report(
        tmp_path / "blocked",
        "samples/runtime_plan_blocked_by_safety_gate.json",
    )
    assert forced.no_action_taken is True
    assert blocked.no_action_taken is True

