import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_reviewed_profile_passes_validate_profile_and_dry_run(tmp_path):
    shadow = tmp_path / "shadow"
    review = tmp_path / "review"
    promoted = tmp_path / "promoted"
    runtime = tmp_path / "runtime"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    assert main([
        "promote-reviewed-profile",
        str(review),
        "--review-decision",
        "samples/review_decision_approved.json",
        "--out",
        str(promoted),
    ]) == EXIT_OK

    profile = promoted / "reviewed_recovery_profile.json"
    assert main(["validate-profile", str(profile)]) == EXIT_OK
    assert main(["dry-run", str(profile), "--out", str(runtime)]) == EXIT_OK
    report = _read(runtime / "runtime_report.json")
    assert report["safety_gate_evaluated"] is True
    assert report["hardware_control_enabled"] is False
