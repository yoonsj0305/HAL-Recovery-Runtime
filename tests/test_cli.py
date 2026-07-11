import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def test_validate_valid_profile_exits_zero(capsys):
    result = main(["validate-profile", "samples/recovery_profile.json"])

    assert result == EXIT_OK
    assert "safety gate passed" in capsys.readouterr().out


def test_dry_run_writes_all_artifacts(tmp_path):
    result = main(
        ["dry-run", "samples/recovery_profile.json", "--out", str(tmp_path)]
    )

    assert result == EXIT_OK
    assert {path.name for path in tmp_path.iterdir()} == {
        "runtime_plan.json",
        "runtime_events.jsonl",
        "runtime_report.json",
    }


def test_validate_unsafe_profile_exits_nonzero(capsys):
    result = main(
        ["validate-profile", "samples/unsafe_hardware_enabled_profile.json"]
    )

    assert result == EXIT_INVALID
    assert "hardware_control_enabled_must_be_false" in capsys.readouterr().err


def test_degraded_dry_run_writes_degraded_report(tmp_path):
    result = main(
        [
            "dry-run",
            "samples/degraded_missing_routes_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = json.loads((tmp_path / "runtime_report.json").read_text(encoding="utf-8"))
    assert result == EXIT_OK
    assert report["degraded_mode_entered"] is True
    assert report["planned_actions"] == 0
    assert report["degraded_mode_reasons"] == ["preferred_routes_missing"]


def test_plan_writes_only_plan_artifact(tmp_path):
    result = main(["plan", "samples/recovery_profile.json", "--out", str(tmp_path)])

    assert result == EXIT_OK
    assert {path.name for path in tmp_path.iterdir()} == {"runtime_plan.json"}


def test_check_compat_valid_profile_exits_zero_without_artifacts(capsys):
    result = main(["check-compat", "samples/recovery_profile.json"])

    assert result == EXIT_OK
    assert "Profile compatible with HAL Recovery Runtime v1.0.0." in capsys.readouterr().out


def test_check_compat_missing_unassigned_workloads_exits_nonzero(capsys):
    result = main(
        [
            "check-compat",
            "samples/unsafe_missing_unassigned_workloads_profile.json",
        ]
    )

    assert result == EXIT_INVALID
    assert "missing unassigned_workloads" in capsys.readouterr().err


def test_validate_missing_unassigned_workloads_exits_nonzero(capsys):
    result = main(
        [
            "validate-profile",
            "samples/unsafe_missing_unassigned_workloads_profile.json",
        ]
    )

    assert result == EXIT_INVALID
    assert "missing_unassigned_workloads" in capsys.readouterr().err
