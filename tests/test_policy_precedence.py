import json

from hal_runtime.cli import EXIT_INVALID, main
from hal_runtime.policy_config import default_policy_config
from hal_runtime.policy_evaluator import evaluate_policy


def _plan(name="runtime_plan_valid.json"):
    return json.loads(open(f"samples/{name}", encoding="utf-8").read())


def _rollback(**changes):
    report = {
        "rollback_simulation_status": "rollback_plan_generated",
        "rollback_required": False,
        "safe_stop_required": False,
        "no_action_taken": False,
        "simulated_revert_actions_planned": 1,
    }
    report.update(changes)
    return report


def _first(decision):
    return next(result["rule"] for result in decision.policy_rule_results if result["matched"])


def test_no_action_beats_rollback_and_combined_rollback_beats_single():
    config = default_policy_config()
    no_action = evaluate_policy(_plan(), config, rollback_report=_rollback(no_action_taken=True, rollback_required=True))
    assert no_action.selected_policy == "no_action_taken"
    assert _first(no_action) == "rollback_no_action_taken"
    combined = evaluate_policy(_plan(), config, rollback_report=_rollback(rollback_required=True, safe_stop_required=True))
    assert combined.selected_policy == "rollback_then_safe_stop_simulation_only"
    assert _first(combined) == "rollback_required_with_safe_stop"


def test_rollback_beats_adapter_blocks_and_adapter_boundary_blocks_review():
    adapter_blocks = {"blocked_actions": 1, "adapter_block_reasons": ["unsupported_action_type"]}
    rollback = evaluate_policy(_plan(), default_policy_config(), adapter_blocks, _rollback(rollback_required=True))
    assert rollback.selected_policy == "rollback_simulation_only"
    assert _first(rollback) == "rollback_required"
    boundary = {
        "adapter_simulation_status": "blocked_safety_boundary",
        "blocked_actions": 1,
        "adapter_safety_failure_reasons": ["execution_mode_must_be_dry_run"],
    }
    blocked = evaluate_policy(_plan(), default_policy_config(), boundary)
    assert blocked.policy_status == "blocked_by_safety_boundary"
    assert _first(blocked) == "adapter_safety_boundary"


def test_policy_config_boundary_precedes_runtime_approval(tmp_path):
    result = main([
        "simulate-policy", "samples/runtime_plan_unsafe_hardware_enabled.json",
        "--policy-config", "samples/policy_config_unsafe_retry.json",
        "--out", str(tmp_path),
    ])
    assert result == EXIT_INVALID
    report = json.loads((tmp_path / "policy_report.json").read_text(encoding="utf-8"))
    first = next(item["rule"] for item in report["policy_rule_results"] if item["matched"])
    assert first == "policy_config_safety_boundary"


def test_nonexecutable_source_selects_no_action_and_order_is_stable():
    decision = evaluate_policy(
        _plan("runtime_plan_blocked_by_safety_gate.json"), default_policy_config()
    )
    assert decision.selected_policy == "no_action_taken"
    assert _first(decision) == "source_plan_not_executable"
    assert [item["rule"] for item in decision.policy_rule_results] == list(decision.to_dict()["policy_precedence_order"])
