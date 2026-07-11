import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _build_shadow(tmp_path):
    shadow = tmp_path / "shadow"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    return shadow


def test_build_candidate_review_writes_review_package_without_promotion(tmp_path):
    shadow = _build_shadow(tmp_path)
    review = tmp_path / "review"

    result = main(["build-candidate-review", str(shadow), "--out", str(review)])

    assert result == EXIT_OK
    assert (review / "candidate_review_package.json").is_file()
    assert (review / "candidate_review_report.json").is_file()
    assert (review / "review_decision_template.json").is_file()
    assert (review / "review_trace.jsonl").is_file()
    assert not (review / "reviewed_recovery_profile.json").exists()
    report = _read(review / "candidate_review_report.json")
    assert report["promotion_allowed"] is False
    assert report["promotion_requires_review_decision"] is True
    assert report["review_gate_matrix"]["human_review_decision_gate"]["status"] == "pending"
