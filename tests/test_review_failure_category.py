import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _review(tmp_path):
    shadow, review = tmp_path / "shadow", tmp_path / "review"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    return review


def test_failure_categories_are_specific(tmp_path):
    review = _review(tmp_path)
    cases = (
        (tmp_path / "absent.json", "missing_review_decision"),
        ("samples/review_decision_invalid_json.json", "invalid_review_decision_json"),
        ("samples/review_decision_wrong_scope_hardware.json", "wrong_approval_scope"),
        ("samples/review_decision_unapproved.json", "human_approval_missing"),
        ("samples/review_decision_empty_reviewer.json", "reviewer_identity_missing"),
        ("samples/review_decision_missing_timestamp.json", "review_timestamp_missing"),
        ("samples/review_decision_missing_ack.json", "acknowledgement_missing"),
        ("samples/review_decision_unsafe_certification.json", "decision_safety_boundary"),
    )
    for index, (decision, category) in enumerate(cases):
        out = tmp_path / f"blocked-{index}"
        assert main(["promote-reviewed-profile", str(review), "--review-decision", str(decision), "--out", str(out)]) == EXIT_INVALID
        assert _read(out / "profile_promotion_report.json")["review_failure_category"] == category
        assert not (out / "reviewed_recovery_profile.json").exists()


def test_validate_without_decision_is_nonfatal_pending(tmp_path):
    review, out = _review(tmp_path), tmp_path / "pending"
    assert main(["validate-candidate-review", str(review), "--out", str(out)]) == EXIT_OK
    report = _read(out / "candidate_review_validation_report.json")
    assert report["review_failure_category"] == "missing_review_decision"
    assert report["promotion_would_be_allowed"] is False

