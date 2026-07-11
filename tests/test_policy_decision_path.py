import json

from hal_runtime.cli import EXIT_INVALID, main
from hal_runtime.policy_config import default_policy_config
from hal_runtime.policy_evaluator import evaluate_policy


def _plan():
    return json.loads(open("samples/runtime_plan_valid.json", encoding="utf-8").read())


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


def test_default_path_records_load_precedence_and_final_selection():
    decision = evaluate_policy(_plan(), default_policy_config())
    steps = [item["step"] for item in decision.policy_decision_path]
    assert steps == ["runtime_plan_loaded", "policy_config_loaded", "policy_precedence_evaluated", "policy_decision_selected"]
    final = decision.policy_decision_path[-1]
    assert final["selected_policy"] == "human_review_required"
    assert final["policy_status"] == "policy_requires_human_review"


def test_rollback_and_safe_stop_paths_record_matched_rule():
    rollback = evaluate_policy(_plan(), default_policy_config(), rollback_report=_rollback(rollback_required=True))
    assert rollback.policy_decision_path[-1]["matched_rule"] == "rollback_required"
    safe_stop = evaluate_policy(_plan(), default_policy_config(), rollback_report=_rollback(safe_stop_required=True))
    assert safe_stop.policy_decision_path[-1]["matched_rule"] == "safe_stop_required"


def test_unsafe_config_path_records_boundary_failure(tmp_path):
    assert main([
        "simulate-policy", "samples/runtime_plan_valid.json",
        "--policy-config", "samples/policy_config_unsafe_allow_real_execution.json",
        "--out", str(tmp_path),
    ]) == EXIT_INVALID
    decision = json.loads((tmp_path / "policy_decision.json").read_text(encoding="utf-8"))
    assert "policy_safety_boundary_failed" in {item["step"] for item in decision["policy_decision_path"]}
    assert decision["policy_decision_path"][-1]["matched_rule"] == "policy_config_safety_boundary"
