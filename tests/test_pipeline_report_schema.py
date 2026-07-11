import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_pipeline_report_summary_and_index_required_fields(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    summary = _read(tmp_path / "pipeline_summary.json")
    report = _read(tmp_path / "pipeline_report.json")
    index = _read(tmp_path / "pipeline_artifact_index.json")
    assert result == EXIT_OK
    for payload in (summary, report, index):
        assert payload["runtime_version"] == "1.0.0"
        assert payload["pipeline_runner_version"] == "1.0.0"
        assert payload["simulation_only"] is True
        assert payload["hardware_control_enabled"] is False
        assert payload["claim_boundary"] == "simulation_only_not_certified"
        assert payload["pipeline_id"] == "PIPELINE_001"
    assert "stage_results" in report
    assert "runtime_summary" in report
    assert "policy_summary" in report
    assert "evidence_summary" in report
    assert "artifacts" in index
    assert "simulation_only" in report["known_limitations"]
    assert "no_hardware_control" in report["known_limitations"]
    assert report["policy_summary"]["hardware_control_allowed"] is False
    assert report["policy_summary"]["real_execution_allowed"] is False


def test_pipeline_report_does_not_claim_certification_or_hardware_readiness(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    report_text = (tmp_path / "pipeline_report.json").read_text(encoding="utf-8").lower()
    assert result == EXIT_OK
    assert "certified_runtime" not in report_text
    assert "certified_recovery" not in report_text
    assert "hardware_ready" not in report_text
    assert "production_ready" not in report_text
