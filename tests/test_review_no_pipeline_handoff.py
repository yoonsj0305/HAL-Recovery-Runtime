import pytest

from hal_runtime.cli import EXIT_OK, main


def test_review_commands_do_not_create_pipeline_artifacts(tmp_path):
    shadow = tmp_path / "shadow"
    review = tmp_path / "review"
    promoted = tmp_path / "promoted"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert not (shadow / "candidate_review_package.json").exists()
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    assert not (review / "reviewed_recovery_profile.json").exists()
    assert main([
        "promote-reviewed-profile",
        str(review),
        "--review-decision",
        "samples/review_decision_approved.json",
        "--out",
        str(promoted),
    ]) == EXIT_OK
    for root in (review, promoted):
        names = {path.name for path in root.iterdir()}
        assert not {"runtime", "adapter", "failure", "policy", "evidence"}.intersection(names)
        assert not any(name.startswith("pipeline_") for name in names)


def test_run_pipeline_still_rejects_shadow_input(tmp_path):
    with pytest.raises(SystemExit):
        main(["run-pipeline", "--shadow-input", "samples/shadow_input_valid", "--out", str(tmp_path)])
