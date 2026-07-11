import json

from hal_runtime.adapter_simulator import simulate_plan_file
from hal_runtime.policy_simulator import simulate_policy_file
from hal_runtime.rollback_simulator import simulate_failure_file


def test_missing_optional_inputs_and_default_config_are_explicit(tmp_path):
    outcome = simulate_policy_file("samples/runtime_plan_valid.json", tmp_path)
    summary = outcome.report.to_dict()["policy_input_summary"]
    assert summary["adapter_report_present"] is False
    assert summary["adapter_simulation_status"] is None
    assert summary["rollback_report_present"] is False
    assert summary["rollback_simulation_status"] is None
    assert summary["policy_config_present"] is False
    assert summary["policy_config_mode"] == "conservative_default"


def test_adapter_summary_populates_blocked_action_count(tmp_path):
    adapter_dir = tmp_path / "adapter"
    simulate_plan_file("samples/runtime_plan_with_unknown_action.json", adapter_dir)
    policy = simulate_policy_file(
        "samples/runtime_plan_with_unknown_action.json",
        tmp_path / "policy",
        adapter_report_path=adapter_dir / "adapter_report.json",
    )
    summary = policy.report.to_dict()["policy_input_summary"]
    assert summary["adapter_report_present"] is True
    assert summary["adapter_blocked_actions"] == 1


def test_rollback_summary_populates_all_decision_flags(tmp_path):
    rollback_dir = tmp_path / "rollback"
    simulate_failure_file(
        "samples/runtime_plan_two_actions.json",
        rollback_dir,
        "samples/failure_scenario_adapter_unavailable_after_first_action.json",
    )
    policy = simulate_policy_file(
        "samples/runtime_plan_two_actions.json",
        tmp_path / "policy",
        rollback_report_path=rollback_dir / "rollback_report.json",
    )
    summary = policy.report.to_dict()["policy_input_summary"]
    assert summary["rollback_report_present"] is True
    assert summary["rollback_required"] is True
    assert summary["safe_stop_required"] is True
    assert summary["no_action_taken"] is False
