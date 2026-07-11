import json

from hal_runtime.cli import main


REQUIRED = {
    "runtime_version", "policy_simulation_version", "simulation_only",
    "hardware_control_enabled", "claim_boundary", "plan_loaded",
    "adapter_report_loaded", "rollback_report_loaded", "policy_config_loaded",
    "policy_config_id", "policy_mode", "selected_policy", "policy_status",
    "human_review_required", "retry_allowed", "real_execution_allowed",
    "hardware_control_allowed", "source_plan_summary", "adapter_report_summary",
    "rollback_report_summary", "policy_reasons", "blocked_reasons",
    "warning_reasons", "decision_confidence", "known_limitations",
}


def test_policy_report_has_stable_schema(tmp_path):
    main(["simulate-policy", "samples/runtime_plan_valid.json", "--out", str(tmp_path)])
    report = json.loads((tmp_path / "policy_report.json").read_text(encoding="utf-8"))
    assert REQUIRED <= report.keys()
    assert report["runtime_version"] == report["policy_simulation_version"] == "1.0.0"
    assert report["decision_confidence"] in {"simulation_only_low_certainty", "simulation_only_medium_certainty", "blocked_or_invalid"}
