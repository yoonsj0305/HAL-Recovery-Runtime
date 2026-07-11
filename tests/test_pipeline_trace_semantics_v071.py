import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_trace_records_terminal_state_and_consistency(tmp_path):
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
    assert result == EXIT_OK
    assert any(event["event_type"] == "pipeline_terminal_state_recorded" for event in events)
    assert any(event["event_type"] == "pipeline_consistency_checked" for event in events)
    assert events[-1]["event_type"] == "pipeline_completed"


def test_trace_records_skipped_evidence_and_blocked_terminal_state(tmp_path):
    noev = tmp_path / "noev"
    blocked = tmp_path / "blocked"
    assert main(["run-pipeline", "--profile", "samples/recovery_profile.json", "--no-evidence", "--out", str(noev)]) == EXIT_OK
    assert main(["run-pipeline", "--profile", "samples/unsafe_hardware_enabled_profile.json", "--out", str(blocked)]) == EXIT_INVALID
    noev_events = _events(noev / "pipeline_trace.jsonl")
    blocked_events = _events(blocked / "pipeline_trace.jsonl")
    assert any(
        event["event_type"] == "pipeline_stage_skipped"
        and event["stage_name"] == "evidence_bundle"
        and event["reason"] == "evidence_disabled"
        for event in noev_events
    )
    assert any(
        event["event_type"] == "pipeline_terminal_state_recorded"
        and event["status"] == "blocked"
        and event["pipeline_terminal_stage"] == "runtime_dry_run"
        and event["pipeline_exit_reason"] == "blocked_by_safety_gate"
        for event in blocked_events
    )
