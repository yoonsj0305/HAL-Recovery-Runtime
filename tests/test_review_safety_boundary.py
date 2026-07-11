import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _shadow(tmp_path):
    shadow = tmp_path / "shadow"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    return shadow


def test_unsafe_candidate_blocks_review_build(tmp_path):
    shadow = _shadow(tmp_path)
    candidate_path = shadow / "recovery_profile_candidate.json"
    candidate = _read(candidate_path)
    candidate["hardware_execution_enabled"] = True
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    result = main(["build-candidate-review", str(shadow), "--out", str(tmp_path / "review")])

    report = _read(tmp_path / "review" / "candidate_review_report.json")
    assert result == EXIT_INVALID
    assert "candidate_hardware_execution_enabled_true" in report[
        "candidate_review_blocking_reasons"
    ]


def test_candidate_assigned_workloads_blocks_review_build(tmp_path):
    shadow = _shadow(tmp_path)
    candidate_path = shadow / "recovery_profile_candidate.json"
    candidate = _read(candidate_path)
    candidate["assigned_workloads"] = [{"workload_id": "W1"}]
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    result = main(["build-candidate-review", str(shadow), "--out", str(tmp_path / "review")])

    report = _read(tmp_path / "review" / "candidate_review_report.json")
    assert result == EXIT_INVALID
    assert "candidate_assigned_workloads_not_allowed_v1_0_0" in report[
        "candidate_review_blocking_reasons"
    ]


def test_review_outputs_do_not_claim_certification_or_hardware_safety(tmp_path):
    shadow = _shadow(tmp_path)
    review = tmp_path / "review"
    assert main(["build-candidate-review", str(shadow), "--out", str(review)]) == EXIT_OK
    output_text = "\n".join(path.read_text(encoding="utf-8") for path in review.iterdir())
    assert '"certification_passed": true' not in output_text
    assert '"safe_for_hardware_control": true' not in output_text
