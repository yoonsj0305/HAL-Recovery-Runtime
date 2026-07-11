import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_normal_pipeline_evidence_summary_records_ran_state(tmp_path):
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
    evidence = report["evidence_summary"]
    assert result == EXIT_OK
    assert evidence["evidence_stage_present"] is True
    assert evidence["evidence_stage_ran"] is True
    assert evidence["evidence_stage_skipped"] is False
    assert evidence["evidence_skip_reason"] is None
    assert report["pipeline_consistency_checks"]["evidence_summary_matches_stage_result"] is True


def test_skipped_evidence_summary_reasons_are_precise(tmp_path):
    noev = tmp_path / "noev"
    unsafe_profile = tmp_path / "unsafe_profile"
    unsafe_policy = tmp_path / "unsafe_policy"
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/recovery_profile.json",
                "--no-evidence",
                "--out",
                str(noev),
            ]
        )
        == EXIT_OK
    )
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/unsafe_hardware_enabled_profile.json",
                "--out",
                str(unsafe_profile),
            ]
        )
        == EXIT_INVALID
    )
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/recovery_profile.json",
                "--policy-config",
                "samples/policy_config_unsafe_allow_real_execution.json",
                "--out",
                str(unsafe_policy),
            ]
        )
        == EXIT_INVALID
    )
    assert _read(noev / "pipeline_report.json")["evidence_summary"]["evidence_skip_reason"] == "evidence_disabled"
    assert _read(unsafe_profile / "pipeline_report.json")["evidence_summary"]["evidence_skip_reason"] == "runtime_dry_run_blocked"
    assert _read(unsafe_policy / "pipeline_report.json")["evidence_summary"]["evidence_skip_reason"] == "policy_simulation_blocked"
    assert _read(noev / "pipeline_report.json")["evidence_summary"]["evidence_validation_passed"] is None
