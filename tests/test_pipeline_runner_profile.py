import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_pipeline_profile_writes_end_to_end_artifacts(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    assert result == EXIT_OK
    assert (tmp_path / "runtime" / "runtime_plan.json").is_file()
    assert (tmp_path / "runtime" / "runtime_report.json").is_file()
    assert (tmp_path / "runtime" / "runtime_events.jsonl").is_file()
    assert (tmp_path / "adapter" / "adapter_report.json").is_file()
    assert (tmp_path / "adapter" / "adapter_trace.jsonl").is_file()
    assert (tmp_path / "failure" / "failure_trace.jsonl").is_file()
    assert (tmp_path / "failure" / "rollback_plan.json").is_file()
    assert (tmp_path / "failure" / "rollback_report.json").is_file()
    assert (tmp_path / "policy" / "policy_trace.jsonl").is_file()
    assert (tmp_path / "policy" / "policy_decision.json").is_file()
    assert (tmp_path / "policy" / "policy_report.json").is_file()
    assert (tmp_path / "evidence" / "evidence_manifest.json").is_file()
    assert (tmp_path / "evidence" / "evidence_bundle.json").is_file()
    assert (tmp_path / "evidence" / "evidence_report.json").is_file()
    assert (tmp_path / "evidence" / "evidence_trace.jsonl").is_file()
    assert (tmp_path / "pipeline_summary.json").is_file()
    assert (tmp_path / "pipeline_report.json").is_file()
    assert (tmp_path / "pipeline_artifact_index.json").is_file()
    assert (tmp_path / "pipeline_trace.jsonl").is_file()

    summary = _read(tmp_path / "pipeline_summary.json")
    report = _read(tmp_path / "pipeline_report.json")
    assert summary["pipeline_status"] in {
        "pipeline_completed",
        "pipeline_completed_with_warnings",
    }
    assert report["simulation_only"] is True
    assert report["hardware_control_enabled"] is False
    assert report["claim_boundary"] == "simulation_only_not_certified"
    assert _read(tmp_path / "runtime" / "runtime_report.json")["runtime_version"] == "1.0.0"
