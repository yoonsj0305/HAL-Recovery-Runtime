import json

from hal_runtime.dry_run_executor import run_dry_run


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_valid_dry_run_writes_all_artifacts(tmp_path):
    result = run_dry_run("samples/recovery_profile.json", tmp_path)

    assert (tmp_path / "runtime_plan.json").is_file()
    assert (tmp_path / "runtime_events.jsonl").is_file()
    assert (tmp_path / "runtime_report.json").is_file()
    assert result.report.runtime_status == "dry_run_passed"
    report = _read_json(tmp_path / "runtime_report.json")
    assert report["planned_actions"] == 1
    assert report["runtime_version"] == "1.0.0"
    assert report["safety_failure_reasons"] == []
    assert report["degraded_mode_reasons"] == []
    assert _read_json(tmp_path / "runtime_plan.json")["runtime_version"] == "1.0.0"
    assert report["bundle_mode"] is False
    assert report["bundle_gate_evaluated"] is False
    assert report["safety_gate_evaluated"] is True
    assert report["execution_gate_stage"] == "dry_run_completed"

    events = [
        json.loads(line)
        for line in (tmp_path / "runtime_events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert all("event_type" in event and "status" in event for event in events)
    assert events[-1] == {"event_type": "dry_run_completed", "status": "ok"}


def test_unsafe_profile_is_blocked_without_actions(tmp_path):
    result = run_dry_run("samples/unsafe_hardware_enabled_profile.json", tmp_path)

    assert result.report.runtime_status == "blocked_by_safety_gate"
    assert result.plan.actions == ()
    assert _read_json(tmp_path / "runtime_plan.json")["actions"] == []
    report = _read_json(tmp_path / "runtime_report.json")
    assert report["safety_gate_passed"] is False
    assert report["planned_actions"] == 0
    assert report["degraded_mode_entered"] is False
    assert report["safety_failure_reasons"] == [
        "hardware_control_enabled_must_be_false"
    ]
    assert report["degraded_mode_reasons"] == []
    assert report["safety_gate_evaluated"] is True
    assert report["execution_gate_stage"] == "single_file_safety_gate"


def test_degraded_profile_writes_no_execution_plan(tmp_path):
    result = run_dry_run("samples/degraded_missing_routes_profile.json", tmp_path)

    report = _read_json(tmp_path / "runtime_report.json")
    assert result.plan.actions == ()
    assert report["degraded_mode_entered"] is True
    assert report["runtime_status"] == "degraded_no_execution_plan"
    assert report["safety_failure_reasons"] == []
    assert report["degraded_mode_reasons"] == ["preferred_routes_missing"]


def test_unknown_action_is_recorded_and_dry_run_continues(tmp_path):
    result = run_dry_run("samples/unknown_action_profile.json", tmp_path)

    assert len(result.plan.actions) == 1
    assert len(result.plan.blocked_actions) == 1
    assert result.report.runtime_status == "dry_run_completed_with_blocks"


def test_missing_unassigned_workloads_writes_blocked_report(tmp_path):
    result = run_dry_run(
        "samples/unsafe_missing_unassigned_workloads_profile.json", tmp_path
    )

    report = _read_json(tmp_path / "runtime_report.json")
    assert result.plan.actions == ()
    assert report["runtime_status"] == "blocked_by_safety_gate"
    assert report["safety_failure_reasons"] == ["missing_unassigned_workloads"]
