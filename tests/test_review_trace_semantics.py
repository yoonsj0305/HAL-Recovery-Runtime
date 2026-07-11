import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _events(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _review(tmp_path):
    shadow = tmp_path / "shadow"
    review = tmp_path / "review"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    return review


def test_build_review_trace_contains_gate_events(tmp_path):
    review = _review(tmp_path)
    events = _events(review / "review_trace.jsonl")
    event_types = [event["event_type"] for event in events]
    gates = [event["gate_id"] for event in events if event["event_type"] == "review_gate_evaluated"]

    assert "review_started" in event_types
    assert "review_decision_template_written" in event_types
    assert {
        "candidate_schema_gate",
        "candidate_safety_gate",
        "shadow_quality_gate",
        "conflict_review_gate",
        "human_review_decision_gate",
    } <= set(gates)


def test_promotion_trace_records_success_and_block(tmp_path):
    review = _review(tmp_path)
    promoted = tmp_path / "promoted"
    blocked = tmp_path / "blocked"

    assert main([
        "promote-reviewed-profile",
        str(review),
        "--review-decision",
        "samples/review_decision_approved.json",
        "--out",
        str(promoted),
    ]) == EXIT_OK
    assert main([
        "promote-reviewed-profile",
        str(review),
        "--review-decision",
        "samples/review_decision_unapproved.json",
        "--out",
        str(blocked),
    ]) == EXIT_INVALID
    assert "review_decision_loaded" in [event["event_type"] for event in _events(promoted / "review_trace.jsonl")]
    assert "reviewed_profile_written" in [event["event_type"] for event in _events(promoted / "review_trace.jsonl")]
    assert "promotion_blocked" in [event["event_type"] for event in _events(blocked / "review_trace.jsonl")]
