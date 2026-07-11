from hal_runtime.evidence_bundle_builder import build_evidence_bundle
from hal_runtime.evidence_validator import validate_built_evidence


def test_valid_and_warning_failure_categories(tmp_path):
    valid = build_evidence_bundle("samples/evidence_input_valid", tmp_path / "valid")
    warning = build_evidence_bundle(
        "samples/evidence_input_version_mismatch_warning", tmp_path / "warning"
    )
    assert valid.report["evidence_failure_category"] == "none"
    assert warning.report["evidence_failure_category"] == "warnings_only"


def test_source_invalid_json_is_separate(tmp_path):
    outcome = build_evidence_bundle(
        "samples/evidence_input_invalid_json", tmp_path
    )
    assert outcome.report["evidence_validation_status"] == "invalid_artifact_json"
    assert outcome.report["evidence_failure_category"] == "invalid_json"
    assert "invalid_json:runtime_plan.json" in outcome.report[
        "evidence_validation_reasons"
    ]


def test_built_bundle_failures_are_separate():
    cases = {
        "evidence_bundle_hash_mismatch": "invalid_hash_mismatch",
        "evidence_bundle_missing_manifest_entry": "invalid_missing_manifest_entries",
        "evidence_bundle_missing_copied_artifact": "invalid_missing_copied_artifacts",
    }
    for sample, expected in cases.items():
        report = validate_built_evidence(f"samples/{sample}").report
        assert report["evidence_validation_status"] == expected


def test_safety_violation_remains_blocked(tmp_path):
    root = tmp_path / "unsafe"
    build_evidence_bundle("samples/evidence_input_unsafe_policy", root)
    report = validate_built_evidence(root).report
    assert report["evidence_validation_status"] == "blocked_safety_boundary"
    assert report["evidence_failure_category"] == "safety_boundary"
