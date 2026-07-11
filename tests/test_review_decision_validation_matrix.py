import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


KEYS = {
    "decision_file_present", "json_validity", "approval_scope", "human_approval",
    "reviewer_identity", "review_timestamp", "required_acknowledgements",
    "decision_safety_boundary", "candidate_review_status", "candidate_safety_invariants",
}


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _review(tmp_path):
    shadow, review = tmp_path / "shadow", tmp_path / "review"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    return review


def test_matrix_is_complete_and_maps_decision_failures(tmp_path):
    review = _review(tmp_path)
    cases = (
        ("samples/review_decision_approved.json", EXIT_OK, None),
        ("samples/review_decision_unapproved.json", EXIT_INVALID, "human_approval"),
        ("samples/review_decision_wrong_scope_hardware.json", EXIT_INVALID, "approval_scope"),
        ("samples/review_decision_missing_ack.json", EXIT_INVALID, "required_acknowledgements"),
        ("samples/review_decision_missing_timestamp.json", EXIT_INVALID, "review_timestamp"),
        ("samples/review_decision_unsafe_certification.json", EXIT_INVALID, "decision_safety_boundary"),
    )
    for index, (sample, exit_code, failed_key) in enumerate(cases):
        out = tmp_path / f"case-{index}"
        assert main(["validate-candidate-review", str(review), "--review-decision", sample, "--out", str(out)]) == exit_code
        matrix = _read(out / "candidate_review_validation_report.json")["review_decision_validation_matrix"]
        assert set(matrix) == KEYS
        if failed_key:
            assert matrix[failed_key]["passed"] is False
        else:
            assert all(item["passed"] for item in matrix.values())

