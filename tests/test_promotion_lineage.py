import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_promotion_lineage_records_only_hash_continuity(tmp_path):
    shadow, review, promoted = (tmp_path / name for name in ("shadow", "review", "promoted"))
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    assert main(["promote-reviewed-profile", str(review), "--review-decision", "samples/review_decision_approved.json", "--out", str(promoted)]) == EXIT_OK
    report_lineage = _read(promoted / "profile_promotion_report.json")["profile_promotion_lineage"]
    profile = _read(promoted / "reviewed_recovery_profile.json")
    assert profile["profile_promotion_lineage"] == report_lineage
    assert report_lineage["promotion_scope"] == "dry_run_only"
    assert all(len(report_lineage[key]) == 64 for key in (
        "candidate_profile_sha256", "candidate_review_package_sha256",
        "candidate_review_report_sha256", "review_decision_sha256",
    ))
    assert profile["profile_origin"]["lineage_hashes_present"] is True
    assert ":\\" not in json.dumps(report_lineage)

