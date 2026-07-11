import json

from hal_runtime.policy_config import default_policy_config, policy_config_from_mapping
from hal_runtime.policy_evaluator import evaluate_policy


def _plan(name="runtime_plan_valid.json"):
    return json.loads(open(f"samples/{name}", encoding="utf-8").read())


def _rollback(**changes):
    report = {
        "rollback_required": False, "safe_stop_required": False,
        "no_action_taken": False, "simulated_revert_actions_planned": 0,
        "rollback_simulation_status": "rollback_not_required",
    }
    report.update(changes)
    return report


def test_default_valid_plan_requires_human_review():
    result = evaluate_policy(_plan(), default_policy_config())
    assert result.selected_policy == "human_review_required"
    assert result.retry_allowed is result.real_execution_allowed is result.hardware_control_allowed is False


def test_rollback_and_safe_stop_precedence():
    config = default_policy_config()
    assert evaluate_policy(_plan(), config, rollback_report=_rollback(rollback_required=True)).selected_policy == "rollback_simulation_only"
    both = evaluate_policy(_plan(), config, rollback_report=_rollback(rollback_required=True, safe_stop_required=True))
    assert both.selected_policy == "rollback_then_safe_stop_simulation_only"
    stop = evaluate_policy(_plan(), config, rollback_report=_rollback(safe_stop_required=True))
    assert stop.selected_policy == "safe_stop_simulation_only"


def test_no_action_adapter_blocks_and_blocked_source():
    config = default_policy_config()
    no_action = evaluate_policy(_plan(), config, rollback_report=_rollback(no_action_taken=True))
    assert no_action.selected_policy == "no_action_taken"
    adapter = {"blocked_actions": 1, "adapter_block_reasons": ["unsupported_action_type"]}
    assert evaluate_policy(_plan(), config, adapter_report=adapter).selected_policy == "human_review_required"
    blocked = evaluate_policy(_plan("runtime_plan_blocked_by_safety_gate.json"), config)
    assert blocked.selected_policy == "no_action_taken"


def test_degraded_and_no_retry_modes_require_review():
    degraded = evaluate_policy(_plan("runtime_plan_degraded_no_execution_plan.json"), default_policy_config())
    assert degraded.selected_policy == "human_review_required"
    raw = json.loads(open("samples/policy_config_conservative_default.json", encoding="utf-8").read())
    raw["policy_mode"] = "no_retry_v0_5_0"
    result = evaluate_policy(_plan(), policy_config_from_mapping(raw))
    assert "retry_forbidden_in_v0_5_0" in result.policy_reasons
    assert result.retry_allowed is False
