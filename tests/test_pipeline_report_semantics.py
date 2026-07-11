import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _stage(report, name):
    return next(item for item in report["stage_results"] if item["stage_name"] == name)


def test_pipeline_report_includes_semantics_version_and_stage_flags(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    assert result == EXIT_OK
    assert report["pipeline_report_semantics_version"] == "1.0.0"
    for stage in report["stage_results"]:
        assert {
            "stage_ran",
            "stage_skipped",
            "stage_blocked",
            "stage_failed",
            "stage_warning",
            "skip_reason",
            "block_reason",
            "failure_reason",
        } <= stage.keys()
    runtime = _stage(report, "runtime_dry_run")
    assert runtime["stage_status"] == "completed"
    assert runtime["stage_ran"] is True
    assert runtime["stage_skipped"] is False


def test_skipped_and_blocked_stages_have_precise_reason_fields(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/unsafe_hardware_enabled_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    runtime = _stage(report, "runtime_dry_run")
    evidence = _stage(report, "evidence_bundle")
    assert result == EXIT_INVALID
    assert runtime["stage_blocked"] is True
    assert runtime["stage_ran"] is True
    assert runtime["block_reason"] == "blocked_by_safety_gate"
    assert evidence["stage_skipped"] is True
    assert evidence["stage_ran"] is False
    assert evidence["skip_reason"] == "runtime_dry_run_blocked"
