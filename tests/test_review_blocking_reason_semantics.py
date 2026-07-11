import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _review(tmp_path):
    shadow, review = tmp_path / "shadow", tmp_path / "review"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    return review


def test_decision_blocking_reasons_are_stable_and_sorted(tmp_path):
    review = _review(tmp_path)
    cases = (
        ("samples/review_decision_wrong_scope_hardware.json", "review_decision_approved_for_not_dry_run_only"),
        ("samples/review_decision_missing_timestamp.json", "review_decision_review_timestamp_missing"),
        ("samples/review_decision_unsafe_certification.json", "review_decision_certification_passed_true"),
    )
    for index, (sample, reason) in enumerate(cases):
        out = tmp_path / f"case-{index}"
        assert main(["promote-reviewed-profile", str(review), "--review-decision", sample, "--out", str(out)]) == EXIT_INVALID
        reasons = _read(out / "profile_promotion_report.json")["promotion_blocking_reasons"]
        assert reasons == sorted(reasons)
        assert reason in reasons


def test_assigned_workload_candidate_uses_v091_reason(tmp_path):
    review = _review(tmp_path)
    package_path = review / "candidate_review_package.json"
    package = _read(package_path)
    package["candidate_profile_snapshot"]["assigned_workloads"] = ["workload"]
    package_path.write_text(json.dumps(package), encoding="utf-8")
    out = tmp_path / "blocked"
    assert main(["promote-reviewed-profile", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(out)]) == EXIT_INVALID
    assert "candidate_assigned_workloads_not_allowed_v1_0_0" in _read(out / "profile_promotion_report.json")["promotion_blocking_reasons"]

