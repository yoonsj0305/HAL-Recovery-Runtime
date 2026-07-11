from hal_runtime.adapter_simulator import load_runtime_plan
from hal_runtime.failure_injector import inject_failure
from hal_runtime.failure_models import load_failure_scenario, scenario_from_mapping
from hal_runtime.rollback_planner import build_rollback_plan


def _scenario(path):
    return scenario_from_mapping(load_failure_scenario(path))


def test_partial_failure_creates_simulated_revert():
    plan = load_runtime_plan("samples/runtime_plan_two_actions.json")
    scenario = _scenario("samples/failure_scenario_partial_plan_failure.json")
    rollback = build_rollback_plan(plan, scenario, inject_failure(plan, scenario))
    assert rollback.rollback_plan_status == "planned_simulation_only"
    assert rollback.rollback_actions[0].rollback_action_type == "simulated_revert"
    assert rollback.rollback_actions[0].source_action_id == "ACT_001"


def test_no_failure_has_no_rollback_actions():
    plan = load_runtime_plan("samples/runtime_plan_valid.json")
    scenario = _scenario("samples/failure_scenario_none.json")
    rollback = build_rollback_plan(plan, scenario, inject_failure(plan, scenario))
    assert rollback.rollback_plan_status == "rollback_not_required"
    assert rollback.rollback_actions == ()


def test_non_executable_plan_takes_no_action():
    plan = load_runtime_plan("samples/runtime_plan_blocked_by_safety_gate.json")
    scenario = _scenario("samples/failure_scenario_none.json")
    rollback = build_rollback_plan(plan, scenario, inject_failure(plan, scenario))
    assert rollback.rollback_plan_status == "no_action_taken"
    assert rollback.rollback_actions == ()


def test_rollback_actions_are_records_without_command_keys():
    plan = load_runtime_plan("samples/runtime_plan_two_actions.json")
    scenario = _scenario("samples/failure_scenario_partial_plan_failure.json")
    payload = build_rollback_plan(plan, scenario, inject_failure(plan, scenario)).to_dict()
    assert all("command" not in key for action in payload["rollback_actions"] for key in action)

