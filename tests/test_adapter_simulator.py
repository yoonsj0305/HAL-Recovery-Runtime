from copy import deepcopy

from hal_runtime.adapter_simulator import load_runtime_plan, simulate_plan


def test_valid_plan_simulates_through_sensor_adapter():
    outcome = simulate_plan(load_runtime_plan("samples/runtime_plan_valid.json"))

    assert outcome.report.adapter_simulation_status == "adapter_simulation_passed"
    assert outcome.report.simulated_actions == 1
    assert outcome.report.blocked_actions == 0
    assert outcome.report.adapter_results[0].adapter_id == "mock_sensor_tile_adapter"
    assert outcome.report.adapter_results[0].simulation_status == "simulated"


def test_unsupported_action_is_blocked():
    outcome = simulate_plan(
        load_runtime_plan("samples/runtime_plan_with_unknown_action.json")
    )

    assert outcome.report.adapter_simulation_status == "adapter_simulation_completed_with_blocks"
    assert outcome.report.simulated_actions == 0
    assert outcome.report.blocked_actions == 1
    assert outcome.report.adapter_results[0].simulation_status == "blocked_unsupported_action"


def test_blocked_plan_is_skipped():
    outcome = simulate_plan(
        load_runtime_plan("samples/runtime_plan_blocked_by_safety_gate.json")
    )

    assert outcome.report.adapter_simulation_status == "skipped_plan_not_executable"
    assert outcome.report.simulated_actions == 0


def test_degraded_plan_is_skipped():
    outcome = simulate_plan(
        load_runtime_plan("samples/runtime_plan_degraded_no_execution_plan.json")
    )

    assert outcome.report.adapter_simulation_status == "skipped_plan_not_executable"
    assert outcome.report.simulated_actions == 0


def test_missing_required_field_is_invalid_plan():
    plan = load_runtime_plan("samples/runtime_plan_valid.json")
    plan.pop("plan_block_reasons")

    outcome = simulate_plan(plan)

    assert outcome.report.adapter_simulation_status == "invalid_plan"
    assert outcome.report.simulated_actions == 0


def test_non_string_plan_status_is_invalid_without_exception():
    plan = load_runtime_plan("samples/runtime_plan_valid.json")
    plan["plan_status"] = []

    outcome = simulate_plan(plan)

    assert outcome.report.adapter_simulation_status == "invalid_plan"


def test_simulator_does_not_mutate_plan():
    plan = load_runtime_plan("samples/runtime_plan_valid.json")
    original = deepcopy(plan)

    simulate_plan(plan)

    assert plan == original


def test_missing_role_is_not_silently_guessed():
    plan = load_runtime_plan("samples/runtime_plan_valid.json")
    plan["actions"][0].pop("role")

    outcome = simulate_plan(plan)

    assert outcome.report.adapter_results[0].adapter_id == "unresolved_mock_adapter"
    assert (
        outcome.report.adapter_results[0].simulation_status
        == "blocked_unsupported_role"
    )
    assert (
        outcome.report.adapter_results[0].simulation_reason
        == "role_missing_or_unresolvable"
    )
