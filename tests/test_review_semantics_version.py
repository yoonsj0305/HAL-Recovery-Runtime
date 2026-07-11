import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_review_artifacts_declare_v091_semantics(tmp_path):
    shadow, review, validation, promoted = (tmp_path / name for name in ("shadow", "review", "validation", "promoted"))
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    assert main(["validate-candidate-review", str(review), "--out", str(validation)]) == EXIT_OK
    assert main(["promote-reviewed-profile", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(promoted)]) == EXIT_OK
    for path in (
        review / "review_schema.json",
        review / "candidate_review_package.json",
        review / "candidate_review_report.json",
        review / "review_decision_template.json",
        validation / "candidate_review_validation_report.json",
        promoted / "reviewed_recovery_profile.json",
        promoted / "profile_promotion_report.json",
    ):
        assert _read(path)["review_semantics_version"] == "1.0.0"

