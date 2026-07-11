from hal_runtime.evidence_bundle_builder import build_evidence_bundle
from hal_runtime.evidence_validator import validate_built_evidence


def test_modified_runtime_plan_has_hash_specific_status_and_reason(tmp_path):
    root = tmp_path / "bundle"
    build_evidence_bundle("samples/evidence_input_valid", root)
    (root / "artifacts" / "runtime_plan.json").write_text("{}", encoding="utf-8")
    report = validate_built_evidence(root).report
    assert report["evidence_validation_status"] == "invalid_hash_mismatch"
    assert report["hash_mismatches"] == ["runtime_plan.json"]
    assert report["evidence_validation_reasons"] == [
        "hash_mismatch:runtime_plan.json"
    ]
    assert report["evidence_failure_category"] == "hash_integrity"
    assert report["evidence_validation_stage"] == "copied_artifact_validation"
