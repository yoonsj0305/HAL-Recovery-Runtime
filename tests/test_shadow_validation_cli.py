import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_validate_shadow_data_accepts_valid_shadow_artifacts(tmp_path):
    source = tmp_path / "shadow"
    validation = tmp_path / "validation"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(source)]) == EXIT_OK

    result = main(["validate-shadow-data", str(source), "--out", str(validation)])

    report = _read(validation / "shadow_validation_report.json")
    assert result == EXIT_OK
    assert report["shadow_validation_status"] == "valid_shadow_data"
    assert report["shadow_validation_passed"] is True


def test_validate_shadow_data_reports_missing_artifacts(tmp_path):
    result = main(["validate-shadow-data", str(tmp_path), "--out", str(tmp_path / "out")])

    report = _read(tmp_path / "out" / "shadow_validation_report.json")
    assert result == EXIT_INVALID
    assert report["shadow_validation_status"] == "invalid_missing_shadow_artifacts"
    assert "missing_shadow_artifact:shadow_observations.json" in report["validation_reasons"]


def test_validate_shadow_data_blocks_candidate_boundary_violation(tmp_path):
    source = tmp_path / "shadow"
    validation = tmp_path / "validation"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(source)]) == EXIT_OK
    candidate_path = source / "recovery_profile_candidate.json"
    candidate = _read(candidate_path)
    candidate["hardware_control_enabled"] = True
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    result = main(["validate-shadow-data", str(source), "--out", str(validation)])

    report = _read(validation / "shadow_validation_report.json")
    assert result == EXIT_INVALID
    assert report["shadow_validation_status"] == "blocked_safety_boundary"
    assert "recovery_profile_candidate.json.hardware_control_enabled" in report[
        "safety_boundary_violations"
    ]


def test_validate_shadow_data_invalidates_candidate_with_assigned_workloads(tmp_path):
    source = tmp_path / "shadow"
    validation = tmp_path / "validation"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(source)]) == EXIT_OK
    candidate_path = source / "recovery_profile_candidate.json"
    candidate = _read(candidate_path)
    candidate["assigned_workloads"] = [{"workload_id": "W1"}]
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    result = main(["validate-shadow-data", str(source), "--out", str(validation)])

    report = _read(validation / "shadow_validation_report.json")
    assert result == EXIT_INVALID
    assert report["shadow_validation_status"] == "invalid_candidate_profile"
    assert "candidate_assigned_workloads_not_allowed_v1_0_0" in report[
        "validation_reasons"
    ]
