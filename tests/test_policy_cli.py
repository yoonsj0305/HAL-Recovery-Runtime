import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_default_policy_cli_writes_three_artifacts(tmp_path):
    assert main(["simulate-policy", "samples/runtime_plan_valid.json", "--out", str(tmp_path)]) == EXIT_OK
    assert {p.name for p in tmp_path.iterdir()} == {"policy_trace.jsonl", "policy_decision.json", "policy_report.json"}
    assert _read(tmp_path / "policy_decision.json")["selected_policy"] == "human_review_required"


def test_unsafe_config_and_plan_exit_nonzero_with_artifacts(tmp_path):
    unsafe_config = tmp_path / "unsafe-config"
    unsafe_plan = tmp_path / "unsafe-plan"
    assert main(["simulate-policy", "samples/runtime_plan_valid.json", "--policy-config", "samples/policy_config_unsafe_allow_real_execution.json", "--out", str(unsafe_config)]) == EXIT_INVALID
    assert _read(unsafe_config / "policy_report.json")["policy_status"] == "blocked_policy_config_safety_boundary"
    assert main(["simulate-policy", "samples/runtime_plan_unsafe_hardware_enabled.json", "--out", str(unsafe_plan)]) == EXIT_INVALID
    assert (unsafe_plan / "policy_decision.json").is_file()


def test_rollback_report_selects_rollback(tmp_path):
    rollback_dir = tmp_path / "rollback"
    assert main(["simulate-failure", "samples/runtime_plan_two_actions.json", "--scenario", "samples/failure_scenario_partial_plan_failure.json", "--out", str(rollback_dir)]) == EXIT_OK
    policy_dir = tmp_path / "policy"
    assert main(["simulate-policy", "samples/runtime_plan_two_actions.json", "--rollback-report", str(rollback_dir / "rollback_report.json"), "--out", str(policy_dir)]) == EXIT_OK
    assert _read(policy_dir / "policy_decision.json")["selected_policy"] in {"rollback_simulation_only", "rollback_then_safe_stop_simulation_only"}
