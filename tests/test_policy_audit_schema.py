import json

from hal_runtime.cli import EXIT_OK, main


DECISION_AUDIT_FIELDS = {
    "policy_audit_version",
    "policy_precedence_order",
    "policy_decision_path",
    "policy_conflict_reasons",
    "policy_blocking_inputs",
    "policy_warning_inputs",
}


def test_policy_decision_and_report_include_audit_schema(tmp_path):
    assert main([
        "simulate-policy", "samples/runtime_plan_valid.json",
        "--out", str(tmp_path),
    ]) == EXIT_OK
    decision = json.loads((tmp_path / "policy_decision.json").read_text(encoding="utf-8"))
    report = json.loads((tmp_path / "policy_report.json").read_text(encoding="utf-8"))
    assert DECISION_AUDIT_FIELDS <= decision.keys()
    assert DECISION_AUDIT_FIELDS | {"policy_input_summary", "policy_rule_results"} <= report.keys()
    assert decision["policy_audit_version"] == report["policy_audit_version"] == "1.0.0"
    assert decision["policy_precedence_order"] == report["policy_precedence_order"]
    assert decision["policy_decision_path"] == report["policy_decision_path"]


def test_rule_results_cover_every_precedence_rule_in_order(tmp_path):
    main(["simulate-policy", "samples/runtime_plan_valid.json", "--out", str(tmp_path)])
    report = json.loads((tmp_path / "policy_report.json").read_text(encoding="utf-8"))
    assert [result["rule"] for result in report["policy_rule_results"]] == report["policy_precedence_order"]
    assert all({"rule", "matched", "effect", "reason"} <= result.keys() for result in report["policy_rule_results"])
