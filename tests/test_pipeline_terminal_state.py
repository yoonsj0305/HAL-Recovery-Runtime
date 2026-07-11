import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_clean_run_terminal_state_is_pipeline_report(tmp_path):
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
    assert report["pipeline_terminal_stage"] == "pipeline_report"
    assert report["pipeline_exit_reason"] == "pipeline_completed_simulation_only"
    assert report["pipeline_blocking_stage"] is None
    assert report["pipeline_failure_category"] == "none"


def test_blocking_terminal_states_name_blocking_stage_and_category(tmp_path):
    unsafe_profile = tmp_path / "unsafe_profile"
    unsafe_policy = tmp_path / "unsafe_policy"
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
    profile_report = _read(unsafe_profile / "pipeline_report.json")
    policy_report = _read(unsafe_policy / "pipeline_report.json")
    assert profile_report["pipeline_terminal_stage"] == "runtime_dry_run"
    assert profile_report["pipeline_blocking_stage"] == "runtime_dry_run"
    assert profile_report["pipeline_failure_category"] == "runtime_safety_boundary"
    assert policy_report["pipeline_terminal_stage"] == "policy_simulation"
    assert policy_report["pipeline_blocking_stage"] == "policy_simulation"
    assert policy_report["pipeline_failure_category"] == "policy_config_safety_boundary"
