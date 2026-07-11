from copy import deepcopy

from hal_runtime.adapter_simulator import load_runtime_plan
from hal_runtime.failure_injector import inject_failure
from hal_runtime.failure_models import load_failure_scenario, scenario_from_mapping


def _scenario(path):
    return scenario_from_mapping(load_failure_scenario(path))


def test_none_simulates_all_actions():
    result = inject_failure(
        load_runtime_plan("samples/runtime_plan_valid.json"),
        _scenario("samples/failure_scenario_none.json"),
    )
    assert result.simulated_action_ids == ("ACT_001",)
    assert result.failed_action_ids == ()


def test_adapter_unavailable_fails_target():
    result = inject_failure(
        load_runtime_plan("samples/runtime_plan_valid.json"),
        _scenario("samples/failure_scenario_adapter_unavailable.json"),
    )
    assert result.failed_action_ids == ("ACT_001",)
    assert result.rollback_strategy == "safe_stop"


def test_timeout_has_no_retry_reason():
    result = inject_failure(
        load_runtime_plan("samples/runtime_plan_valid.json"),
        _scenario("samples/failure_scenario_action_timeout.json"),
    )
    assert "retry_not_allowed_in_v0_4_1" in result.failure_reasons


def test_route_unavailable_uses_pre_simulation_strategy():
    result = inject_failure(
        load_runtime_plan("samples/runtime_plan_two_actions.json"),
        _scenario("samples/failure_scenario_route_unavailable.json"),
    )
    assert result.simulated_action_ids == ("ACT_001",)
    assert result.rollback_strategy == "rollback_to_pre_simulation_state"


def test_partial_failure_skips_actions_after_target():
    plan = deepcopy(load_runtime_plan("samples/runtime_plan_two_actions.json"))
    plan["actions"].append(
        {"action_id": "ACT_003", "action_type": "assign_workload", "role": "memory_tile"}
    )
    result = inject_failure(
        plan, _scenario("samples/failure_scenario_partial_plan_failure.json")
    )
    assert result.simulated_action_ids == ("ACT_001",)
    assert result.failed_action_ids == ("ACT_002",)
    assert result.skipped_action_ids == ("ACT_003",)


def test_forced_safety_failure_simulates_nothing():
    result = inject_failure(
        load_runtime_plan("samples/runtime_plan_two_actions.json"),
        _scenario("samples/failure_scenario_forced_safety_boundary_failure.json"),
    )
    assert result.simulated_action_ids == ()
    assert result.rollback_strategy == "no_action_taken"
