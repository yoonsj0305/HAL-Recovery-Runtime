import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_validation_matrix_has_all_keys_for_valid_data(tmp_path):
    source = tmp_path / "shadow"
    validation = tmp_path / "validation"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(source)]) == EXIT_OK

    assert main(["validate-shadow-data", str(source), "--out", str(validation)]) == EXIT_OK
    matrix = _read(validation / "shadow_validation_report.json")["shadow_validation_matrix"]

    assert set(matrix) == {
        "shadow_artifacts_present",
        "json_validity",
        "safety_boundary",
        "candidate_invariants",
        "observation_quality",
        "field_coverage",
        "conflict_detection",
    }
    assert matrix["candidate_invariants"]["passed"] is True


def test_shadow_validation_matrix_reports_conflicts_as_warnings(tmp_path):
    source = tmp_path / "shadow"
    validation = tmp_path / "validation"
    assert main(["ingest-shadow-data", "samples/shadow_input_conflict", "--out", str(source)]) == EXIT_OK

    assert main(["validate-shadow-data", str(source), "--out", str(validation)]) == EXIT_OK
    matrix = _read(validation / "shadow_validation_report.json")["shadow_validation_matrix"]

    assert matrix["conflict_detection"]["passed"] is True
    assert matrix["conflict_detection"]["status"] == "warnings_present"
    assert "conflicting_observations:CONFLICT_TILE_00" in matrix["conflict_detection"]["reasons"]


def test_shadow_validation_matrix_invalidates_unsafe_candidate_invariants(tmp_path):
    source = tmp_path / "shadow"
    validation = tmp_path / "validation"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(source)]) == EXIT_OK
    candidate_path = source / "recovery_profile_candidate.json"
    candidate = _read(candidate_path)
    candidate["assigned_workloads"] = [{"workload_id": "W1"}]
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    assert main(["validate-shadow-data", str(source), "--out", str(validation)]) == EXIT_INVALID
    report = _read(validation / "shadow_validation_report.json")
    assert report["shadow_validation_matrix"]["candidate_invariants"]["passed"] is False
    assert "candidate_assigned_workloads_not_allowed_v1_0_0" in report["validation_reasons"]
