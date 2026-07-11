import json

from hal_runtime.cli import main


def _events(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_shadow_trace_contains_quality_events(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(tmp_path)])

    event_types = [event["event_type"] for event in _events(tmp_path / "shadow_trace.jsonl")]

    assert "shadow_quality_computed" in event_types
    assert "shadow_field_coverage_computed" in event_types
    assert "shadow_conflict_matrix_built" in event_types
    assert "shadow_candidate_confidence_summary_built" in event_types


def test_shadow_trace_contains_conflict_event(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_conflict", "--out", str(tmp_path)])

    events = _events(tmp_path / "shadow_trace.jsonl")

    assert any(
        event["event_type"] == "shadow_conflict_detected"
        and event["reason"] == "conflicting_observations:CONFLICT_TILE_00"
        for event in events
    )
