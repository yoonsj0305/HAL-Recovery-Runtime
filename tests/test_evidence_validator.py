import json

from hal_runtime.evidence_bundle_builder import build_evidence_bundle
from hal_runtime.evidence_validator import validate_built_evidence


def _built(tmp_path):
    root = tmp_path / "bundle"
    build_evidence_bundle("samples/evidence_input_valid", root)
    return root


def test_valid_built_bundle_hashes_pass(tmp_path):
    report = validate_built_evidence(_built(tmp_path)).report
    assert report["evidence_validation_passed"] is True
    assert report["hashes_verified"] is True
    assert report["hash_mismatches"] == []


def test_hash_mismatch_is_detected(tmp_path):
    root = _built(tmp_path)
    (root / "artifacts" / "runtime_plan.json").write_text("{}", encoding="utf-8")
    report = validate_built_evidence(root).report
    assert report["evidence_validation_passed"] is False
    assert "runtime_plan.json" in report["hash_mismatches"]


def test_missing_manifest_entry_is_detected(tmp_path):
    root = _built(tmp_path)
    path = root / "evidence_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["artifacts"] = manifest["artifacts"][1:]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    report = validate_built_evidence(root).report
    assert report["missing_manifest_entries"]
    assert report["evidence_validation_passed"] is False


def test_evidence_report_boundary_violation_is_detected(tmp_path):
    root = _built(tmp_path)
    path = root / "evidence_report.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["hardware_control_enabled"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = validate_built_evidence(root).report
    assert report["evidence_validation_status"] == "blocked_safety_boundary"
    assert report["safety_boundary_violations"]
