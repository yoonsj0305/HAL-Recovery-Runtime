import json

from hal_runtime.cli import EXIT_INVALID, main


def test_dependency_graph_is_reported_and_explains_skip_reason(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/unsafe_hardware_enabled_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = json.loads((tmp_path / "pipeline_report.json").read_text(encoding="utf-8"))
    graph = report["pipeline_dependency_graph"]
    assert result == EXIT_INVALID
    assert graph["runtime_dry_run"] == ["input_load"]
    assert graph["evidence_bundle"] == ["runtime_dry_run", "policy_simulation"]
    assert "runtime_dry_run" in graph["policy_simulation"]
    assert "evidence_bundle:runtime_dry_run_blocked" in report["pipeline_skip_reasons"]
    assert any(
        item["transition"] == "skip"
        and item["to_stage"] == "evidence_bundle"
        and item["reason"] == "runtime_dry_run_blocked"
        for item in report["pipeline_stage_transition_log"]
    )
