import json
from pathlib import Path

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_validate_bundle_writes_standalone_report(tmp_path):
    result = main(
        ["validate-bundle", "samples/compiler_bundle_valid", "--out", str(tmp_path)]
    )

    report = _json(tmp_path / "bundle_validation_report.json")
    assert result == EXIT_OK
    assert report["runtime_version"] == "1.0.0"
    assert report["bundle_mode"] is True
    assert report["bundle_validation_status"] == "valid_bundle"
    assert report["supporting_artifact_count"] == 4
    assert report["validation_stage"] == "validated"


def test_validate_valid_bundle_without_out_writes_nothing(tmp_path, monkeypatch):
    bundle_path = Path("samples/compiler_bundle_valid").resolve()
    monkeypatch.chdir(tmp_path)

    result = main(["validate-bundle", str(bundle_path)])

    assert result == EXIT_OK
    assert list(tmp_path.iterdir()) == []


def test_valid_bundle_dry_run_writes_all_artifacts(tmp_path):
    result = main(
        ["dry-run-bundle", "samples/compiler_bundle_valid", "--out", str(tmp_path)]
    )

    assert result == EXIT_OK
    assert {path.name for path in tmp_path.iterdir()} == {
        "runtime_plan.json",
        "runtime_events.jsonl",
        "runtime_report.json",
    }
    report = _json(tmp_path / "runtime_report.json")
    assert report["bundle_mode"] is True
    assert report["runtime_version"] == "1.0.0"
    assert report["bundle_validation_status"] == "valid_bundle"
    assert report["planned_actions"] == 1
    events = [
        json.loads(line)
        for line in (tmp_path / "runtime_events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event_type"] for event in events[:3]] == [
        "bundle_loaded",
        "compatibility_check_passed",
        "bundle_validation_passed",
    ]
    assert any(event["event_type"] == "plan_built" for event in events)


def test_missing_solver_bundle_degrades_and_continues(tmp_path):
    result = main(
        [
            "dry-run-bundle",
            "samples/compiler_bundle_missing_solver_report",
            "--out",
            str(tmp_path),
        ]
    )

    report = _json(tmp_path / "runtime_report.json")
    assert result == EXIT_OK
    assert report["degraded_bundle_mode"] is True
    assert report["bundle_validation_status"] == "degraded_missing_artifacts"
    assert report["runtime_status"] == "dry_run_passed_with_bundle_warnings"
    assert report["planned_actions"] == 1
    assert "solver_report.json" in report["missing_artifacts"]


def test_profile_id_mismatch_blocks_dry_run(tmp_path):
    result = main(
        [
            "dry-run-bundle",
            "samples/compiler_bundle_mismatch_profile_id",
            "--out",
            str(tmp_path),
        ]
    )

    report = _json(tmp_path / "runtime_report.json")
    plan = _json(tmp_path / "runtime_plan.json")
    assert result == EXIT_INVALID
    assert report["runtime_status"] == "blocked_by_bundle_validation"
    assert report["bundle_validation_passed"] is False
    assert report["planned_actions"] == 0
    assert report["bundle_gate_evaluated"] is True
    assert report["safety_gate_evaluated"] is False
    assert report["execution_gate_stage"] == "bundle_validation_gate"
    assert plan["actions"] == []
    assert plan["blocked_actions"] == []
    assert plan["plan_status"] == "blocked_by_bundle_validation"
    assert plan["plan_block_reasons"]


def test_failed_artifact_validation_exits_nonzero(tmp_path):
    result = main(
        [
            "validate-bundle",
            "samples/compiler_bundle_validation_failed",
            "--out",
            str(tmp_path),
        ]
    )

    report = _json(tmp_path / "bundle_validation_report.json")
    assert result == EXIT_INVALID
    assert report["bundle_validation_status"] == "invalid_artifact_validation_failed"
    assert report["validation_stage"] == "bundle_validation"


def test_missing_profile_validation_report_stops_at_bundle_load(tmp_path):
    bundle = tmp_path / "bundle"
    output = tmp_path / "output"
    bundle.mkdir()

    result = main(["validate-bundle", str(bundle), "--out", str(output)])

    report = _json(output / "bundle_validation_report.json")
    assert result == EXIT_INVALID
    assert report["validation_stage"] == "bundle_load"


def test_bundle_safety_failure_records_safety_stage(tmp_path):
    profile = json.loads(Path("samples/recovery_profile.json").read_text(encoding="utf-8"))
    profile["hardware_control_enabled"] = True
    bundle = tmp_path / "bundle"
    validation_output = tmp_path / "validation"
    run_output = tmp_path / "run"
    bundle.mkdir()
    (bundle / "recovery_profile.json").write_text(json.dumps(profile), encoding="utf-8")

    validation_exit = main(
        ["validate-bundle", str(bundle), "--out", str(validation_output)]
    )
    run_exit = main(["dry-run-bundle", str(bundle), "--out", str(run_output)])

    validation_report = _json(validation_output / "bundle_validation_report.json")
    runtime_report = _json(run_output / "runtime_report.json")
    assert validation_exit == EXIT_INVALID
    assert validation_report["validation_stage"] == "safety_gate"
    assert run_exit == EXIT_INVALID
    assert runtime_report["safety_gate_evaluated"] is True
    assert runtime_report["safety_gate_passed"] is False
    assert runtime_report["execution_gate_stage"] == "bundle_safety_gate"
