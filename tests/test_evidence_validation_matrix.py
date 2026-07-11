from hal_runtime.evidence_bundle_builder import build_evidence_bundle
from hal_runtime.evidence_schema import VALIDATION_MATRIX_KEYS
from hal_runtime.evidence_validator import validate_built_evidence


def test_matrix_always_contains_all_categories(tmp_path):
    root = tmp_path / "bundle"
    build_evidence_bundle("samples/evidence_input_valid", root)
    matrix = validate_built_evidence(root).report["evidence_validation_matrix"]
    assert tuple(matrix) == VALIDATION_MATRIX_KEYS
    assert all({"passed", "status", "reasons"} <= value.keys() for value in matrix.values())


def test_matrix_marks_hash_copy_and_json_failures(tmp_path):
    hash_matrix = validate_built_evidence(
        "samples/evidence_bundle_hash_mismatch"
    ).report["evidence_validation_matrix"]
    copy_matrix = validate_built_evidence(
        "samples/evidence_bundle_missing_copied_artifact"
    ).report["evidence_validation_matrix"]
    assert hash_matrix["hash_integrity"]["passed"] is False
    assert copy_matrix["copied_artifacts"]["passed"] is False
    source = build_evidence_bundle(
        "samples/evidence_input_invalid_json", tmp_path / "invalid_json"
    )
    assert source.report["evidence_validation_matrix"]["json_validity"]["passed"] is False


def test_warning_matrix_does_not_fail_validation(tmp_path):
    root = tmp_path / "warning"
    build_evidence_bundle("samples/evidence_input_version_mismatch_warning", root)
    report = validate_built_evidence(root).report
    assert report["evidence_validation_passed"] is True
    assert report["evidence_validation_matrix"]["warnings"]["status"] == "warnings_present"
