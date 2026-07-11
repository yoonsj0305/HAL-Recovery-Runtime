import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _review(tmp_path):
    shadow, review = tmp_path / "shadow", tmp_path / "review"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    return review


def test_decision_provenance_distinguishes_pending_and_explicit_file(tmp_path):
    review = _review(tmp_path)
    pending, approved, promoted = (tmp_path / name for name in ("pending", "approved", "promoted"))
    assert main(["validate-candidate-review", str(review), "--out", str(pending)]) == EXIT_OK
    assert main(["validate-candidate-review", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(approved)]) == EXIT_OK
    assert main(["promote-reviewed-profile", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(promoted)]) == EXIT_OK
    pending_provenance = _read(pending / "candidate_review_validation_report.json")["review_decision_provenance"]
    approved_provenance = _read(approved / "candidate_review_validation_report.json")["review_decision_provenance"]
    assert pending_provenance["review_decision_loaded"] is False
    assert pending_provenance["review_decision_sha256"] is None
    assert approved_provenance["decision_source"] == "explicit_review_decision_file"
    assert len(approved_provenance["review_decision_sha256"]) == 64
    assert _read(promoted / "profile_promotion_report.json")["review_decision_provenance"] == approved_provenance

