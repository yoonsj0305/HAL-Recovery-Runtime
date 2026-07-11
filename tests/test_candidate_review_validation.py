import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _review(tmp_path):
    shadow = tmp_path / "shadow"
    review = tmp_path / "review"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    return review


def test_validate_candidate_review_without_decision_is_valid_but_not_promotable(tmp_path):
    review = _review(tmp_path)
    out = tmp_path / "validation"

    assert main(["validate-candidate-review", str(review), "--out", str(out)]) == EXIT_OK
    report = _read(out / "candidate_review_validation_report.json")
    assert report["candidate_review_validation_status"] == "valid_candidate_review"
    assert report["promotion_would_be_allowed"] is False
    assert report["review_decision_loaded"] is False


def test_validate_candidate_review_with_approved_decision_is_promotable(tmp_path):
    review = _review(tmp_path)
    out = tmp_path / "validation"

    assert main([
        "validate-candidate-review",
        str(review),
        "--review-decision",
        "samples/review_decision_approved.json",
        "--out",
        str(out),
    ]) == EXIT_OK
    report = _read(out / "candidate_review_validation_report.json")
    assert report["candidate_review_validation_status"] == "promotion_decision_valid"
    assert report["promotion_would_be_allowed"] is True


def test_validate_candidate_review_blocks_bad_decisions(tmp_path):
    review = _review(tmp_path)
    for sample in (
        "samples/review_decision_unapproved.json",
        "samples/review_decision_wrong_scope_hardware.json",
    ):
        out = tmp_path / sample.replace("/", "_")
        assert main([
            "validate-candidate-review",
            str(review),
            "--review-decision",
            sample,
            "--out",
            str(out),
        ]) == EXIT_INVALID
        assert _read(out / "candidate_review_validation_report.json")[
            "candidate_review_validation_status"
        ] == "promotion_decision_blocked"
