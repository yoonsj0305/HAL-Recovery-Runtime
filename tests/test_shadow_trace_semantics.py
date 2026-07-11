import json

from hal_runtime.cli import main


def _events(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_shadow_trace_contains_required_event_shape_for_valid_ingestion(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(tmp_path)])

    events = _events(tmp_path / "shadow_trace.jsonl")
    event_types = [event["event_type"] for event in events]
    assert events
    assert all("event_type" in event and "status" in event for event in events)
    assert event_types[0] == "shadow_ingestion_started"
    assert "shadow_file_discovered" in event_types
    assert "shadow_observation_normalized" in event_types
    assert "shadow_profile_candidate_built" in event_types
    assert event_types[-1] == "shadow_ingestion_completed"
    assert events[-1]["shadow_ingestion_status"] == "shadow_ingestion_completed"


def test_shadow_trace_records_invalid_input_event(tmp_path):
    main(
        [
            "ingest-shadow-data",
            "samples/shadow_input_no_supported_files",
            "--out",
            str(tmp_path),
        ]
    )

    events = _events(tmp_path / "shadow_trace.jsonl")
    assert any(
        event["event_type"] == "shadow_input_invalid"
        and event["reason"] == "invalid_no_supported_files"
        for event in events
    )
    assert events[-1]["status"] == "invalid"
