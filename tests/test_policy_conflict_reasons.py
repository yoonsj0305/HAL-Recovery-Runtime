import json

from hal_runtime.policy_config import default_policy_config
from hal_runtime.policy_evaluator import evaluate_policy


def _plan(name="runtime_plan_valid.json"):
    return json.loads(open(f"samples/{name}", encoding="utf-8").read())


def _rollback(**changes):
    result = {
        "rollback_simulation_status": "rollback_plan_generated",
        "rollback_required": False,
        "safe_stop_required": False,
        "no_action_taken": False,
        "simulated_revert_actions_planned": 1,
    }
    result.update(changes)
    return result


def test_rollback_and_safe_stop_conflict_is_recorded():
    decision = evaluate_policy(_plan(), default_policy_config(), rollback_report=_rollback(rollback_required=True, safe_stop_required=True))
    assert "rollback_and_safe_stop_both_required" in decision.policy_conflict_reasons


def test_adapter_blocks_with_rollback_conflict_is_recorded():
    adapter = {"blocked_actions": 1, "adapter_block_reasons": ["unsupported_action_type"]}
    decision = evaluate_policy(_plan(), default_policy_config(), adapter, _rollback(rollback_required=True))
    assert "adapter_blocks_present_but_rollback_has_higher_precedence" in decision.policy_conflict_reasons


def test_degraded_and_adapter_review_conflict_is_recorded():
    adapter = {"blocked_actions": 1, "adapter_block_reasons": ["unsupported_action_type"]}
    decision = evaluate_policy(_plan("runtime_plan_degraded_no_execution_plan.json"), default_policy_config(), adapter)
    assert "multiple_review_reasons:degraded_plan,adapter_blocks" in decision.policy_conflict_reasons
    assert decision.selected_policy == "human_review_required"


def test_no_action_over_rollback_conflict_is_recorded():
    decision = evaluate_policy(_plan(), default_policy_config(), rollback_report=_rollback(no_action_taken=True, rollback_required=True))
    assert "no_action_takes_precedence_over_rollback" in decision.policy_conflict_reasons
    assert decision.selected_policy == "no_action_taken"
