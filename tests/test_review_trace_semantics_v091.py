import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _types(path):
    return [json.loads(line)["event_type"] for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_v091_review_trace_covers_hash_matrix_preflight_and_lineage(tmp_path):
    shadow, review, validation, promoted, blocked = (tmp_path / name for name in ("shadow", "review", "validation", "promoted", "blocked"))
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    assert "review_artifact_hash_computed" in _types(review / "review_trace.jsonl")
    assert main(["validate-candidate-review", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(validation)]) == EXIT_OK
    assert "review_decision_validation_matrix_built" in _types(validation / "review_trace.jsonl")
    assert main(["promote-reviewed-profile", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(promoted)]) == EXIT_OK
    promoted_types = _types(promoted / "review_trace.jsonl")
    assert "promotion_preflight_checked" in promoted_types
    assert "promotion_artifact_lineage_built" in promoted_types
    assert main(["promote-reviewed-profile", str(review), "--review-decision", "samples/review_decision_wrong_scope_hardware.json", "--out", str(blocked)]) == EXIT_INVALID
    assert "review_decision_blocked" in _types(blocked / "review_trace.jsonl")
