import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _review(tmp_path):
    shadow, review = tmp_path / "shadow", tmp_path / "review"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    return review


def test_preflight_allows_only_valid_explicit_dry_run_decision(tmp_path):
    review = _review(tmp_path)
    valid = tmp_path / "valid"
    assert main(["promote-reviewed-profile", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(valid)]) == EXIT_OK
    assert _read(valid / "profile_promotion_report.json")["promotion_preflight_summary"]["promotion_preflight_passed"] is True
    for index, sample in enumerate((
        "samples/review_decision_wrong_scope_hardware.json",
        "samples/review_decision_missing_ack.json",
    )):
        out = tmp_path / f"invalid-{index}"
        assert main(["promote-reviewed-profile", str(review), "--review-decision", sample, "--out", str(out)]) == EXIT_INVALID
        assert not (out / "reviewed_recovery_profile.json").exists()

