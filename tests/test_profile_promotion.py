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


def test_promote_reviewed_profile_with_valid_decision(tmp_path):
    review = _review(tmp_path)
    promoted = tmp_path / "promoted"

    result = main([
        "promote-reviewed-profile",
        str(review),
        "--review-decision",
        "samples/review_decision_approved.json",
        "--out",
        str(promoted),
    ])

    profile = _read(promoted / "reviewed_recovery_profile.json")
    report = _read(promoted / "profile_promotion_report.json")
    assert result == EXIT_OK
    assert report["promotion_status"] == "profile_promoted_for_dry_run"
    assert profile["human_review_completed"] is True
    assert profile["hardware_execution_enabled"] is False
    assert profile["hardware_control_enabled"] is False
    assert profile["assigned_workloads"] == []
    assert "profile_candidate" not in profile


def test_promote_reviewed_profile_blocks_invalid_decisions(tmp_path):
    review = _review(tmp_path)
    for sample in (
        "samples/review_decision_unapproved.json",
        "samples/review_decision_missing_ack.json",
        "samples/review_decision_wrong_scope_hardware.json",
        "samples/review_decision_wrong_scope_production.json",
    ):
        out = tmp_path / sample.replace("/", "_")
        assert main([
            "promote-reviewed-profile",
            str(review),
            "--review-decision",
            sample,
            "--out",
            str(out),
        ]) == EXIT_INVALID
        assert not (out / "reviewed_recovery_profile.json").exists()
        assert _read(out / "profile_promotion_report.json")["promotion_blocked"] is True
