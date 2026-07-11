import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_unsafe_profile_lists_all_dependent_skip_reasons(tmp_path):
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
    assert result == EXIT_INVALID
    assert report["pipeline_skip_reasons"] == [
        "adapter_simulation:runtime_dry_run_blocked",
        "failure_rollback_simulation:runtime_dry_run_blocked",
        "policy_simulation:runtime_dry_run_blocked",
        "evidence_bundle:runtime_dry_run_blocked",
    ]
    for stage in report["stage_results"]:
        if stage["stage_skipped"]:
            assert stage["skip_reason"]


def test_no_evidence_records_intentional_skip_reason(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--no-evidence",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    assert result == EXIT_OK
    assert "evidence_bundle:evidence_disabled" in report["pipeline_skip_reasons"]
