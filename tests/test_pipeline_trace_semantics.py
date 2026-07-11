import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_success_trace_contains_started_stage_events_and_completion(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    events = _events(tmp_path / "pipeline_trace.jsonl")
    event_types = [event["event_type"] for event in events]
    assert result == EXIT_OK
    assert "pipeline_started" in event_types
    assert any(
        event["event_type"] == "pipeline_stage_started"
        and event["stage_name"] == "runtime_dry_run"
        for event in events
    )
    assert any(
        event["event_type"] == "pipeline_stage_completed"
        and event["stage_name"] == "policy_simulation"
        for event in events
    )
    assert event_types[-1] == "pipeline_completed"


def test_blocked_trace_contains_stage_failed_and_completion(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/unsafe_hardware_enabled_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    events = _events(tmp_path / "pipeline_trace.jsonl")
    assert result == EXIT_INVALID
    assert any(event["event_type"] == "pipeline_stage_failed" for event in events)
    assert events[-1]["pipeline_status"] == "pipeline_blocked"


def test_warning_trace_contains_stage_warning(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--bundle",
            "samples/compiler_bundle_missing_solver_report",
            "--out",
            str(tmp_path),
        ]
    )

    events = _events(tmp_path / "pipeline_trace.jsonl")
    assert result == EXIT_OK
    assert any(event["event_type"] == "pipeline_stage_warning" for event in events)
    assert events[-1]["pipeline_status"] == "pipeline_completed_with_warnings"
