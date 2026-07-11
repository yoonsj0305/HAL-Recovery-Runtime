import shutil

from hal_runtime.evidence_bundle_builder import build_evidence_bundle
from hal_runtime.evidence_validator import validate_built_evidence


def test_safety_beats_hash_mismatch(tmp_path):
    root = tmp_path / "bundle"
    build_evidence_bundle("samples/evidence_input_unsafe_policy", root)
    (root / "artifacts" / "runtime_plan.json").write_text("{}", encoding="utf-8")
    assert validate_built_evidence(root).report["evidence_validation_status"] == "blocked_safety_boundary"


def test_invalid_json_beats_missing_required(tmp_path):
    source = tmp_path / "source"
    shutil.copytree("samples/evidence_input_invalid_json", source)
    (source / "policy_decision.json").unlink()
    outcome = build_evidence_bundle(source, tmp_path / "bundle")
    assert outcome.report["evidence_validation_status"] == "invalid_artifact_json"


def test_missing_required_beats_hash_mismatch(tmp_path):
    root = tmp_path / "bundle"
    build_evidence_bundle("samples/evidence_input_missing_required", root)
    (root / "artifacts" / "runtime_plan.json").write_text("{}", encoding="utf-8")
    report = validate_built_evidence(root).report
    assert report["evidence_validation_status"] == "invalid_missing_required_artifacts"


def test_warning_and_clean_statuses(tmp_path):
    warning = tmp_path / "warning"
    valid = tmp_path / "valid"
    build_evidence_bundle("samples/evidence_input_version_mismatch_warning", warning)
    build_evidence_bundle("samples/evidence_input_valid", valid)
    assert validate_built_evidence(warning).report["evidence_validation_status"] == "valid_with_warnings"
    assert validate_built_evidence(valid).report["evidence_validation_status"] == "valid_evidence_bundle"
