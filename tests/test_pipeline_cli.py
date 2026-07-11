import json

import pytest

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_pipeline_requires_exactly_one_profile_or_bundle(tmp_path):
    assert main(["run-pipeline", "--out", str(tmp_path / "none")]) == EXIT_INVALID
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/recovery_profile.json",
                "--bundle",
                "samples/compiler_bundle_valid",
                "--out",
                str(tmp_path / "both"),
            ]
        )
        == EXIT_INVALID
    )


def test_run_pipeline_missing_out_exits_nonzero():
    with pytest.raises(SystemExit):
        main(["run-pipeline", "--profile", "samples/recovery_profile.json"])


def test_run_pipeline_invalid_profile_path_exits_nonzero(tmp_path):
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/missing_profile.json",
                "--out",
                str(tmp_path),
            ]
        )
        == EXIT_INVALID
    )


def test_valid_profile_and_bundle_commands_exit_zero(tmp_path):
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/recovery_profile.json",
                "--out",
                str(tmp_path / "profile"),
            ]
        )
        == EXIT_OK
    )
    assert (
        main(
            [
                "run-pipeline",
                "--bundle",
                "samples/compiler_bundle_valid",
                "--out",
                str(tmp_path / "bundle"),
            ]
        )
        == EXIT_OK
    )


def test_no_evidence_skips_evidence_stage(tmp_path):
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
    assert report["evidence_summary"]["evidence_stage_skipped"] is True
    assert not (tmp_path / "evidence" / "evidence_bundle.json").exists()


def test_failure_scenario_partial_failure_can_select_rollback_policy(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/pipeline_profile_two_actions.json",
            "--failure-scenario",
            "samples/failure_scenario_partial_plan_failure.json",
            "--policy-config",
            "samples/policy_config_rollback_if_prior_actions.json",
            "--out",
            str(tmp_path),
        ]
    )

    summary = _read(tmp_path / "pipeline_summary.json")
    rollback = _read(tmp_path / "failure" / "rollback_report.json")
    assert result == EXIT_OK
    assert rollback["rollback_required"] is True
    assert summary["final_selected_policy"] == "rollback_simulation_only"
