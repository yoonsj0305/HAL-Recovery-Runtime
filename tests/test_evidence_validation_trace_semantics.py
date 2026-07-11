from hal_runtime.evidence_bundle_builder import build_evidence_bundle
from hal_runtime.evidence_validator import validate_built_evidence


def _kinds(outcome):
    return {event["event_type"] for event in outcome.trace_events}


def test_precise_invalid_validation_events():
    cases = {
        "evidence_bundle_hash_mismatch": "evidence_hash_mismatch_detected",
        "evidence_bundle_missing_manifest_entry": "evidence_manifest_entry_missing",
        "evidence_bundle_missing_copied_artifact": "evidence_copied_artifact_missing",
    }
    for sample, event_type in cases.items():
        assert event_type in _kinds(validate_built_evidence(f"samples/{sample}"))


def test_invalid_json_build_trace_is_precise(tmp_path):
    outcome = build_evidence_bundle("samples/evidence_input_invalid_json", tmp_path)
    assert "evidence_artifact_json_invalid" in {
        event["event_type"] for event in outcome.trace_events
    }


def test_warning_and_valid_validation_events(tmp_path):
    warning = tmp_path / "warning"
    valid = tmp_path / "valid"
    build_evidence_bundle("samples/evidence_input_version_mismatch_warning", warning)
    build_evidence_bundle("samples/evidence_input_valid", valid)
    warning_outcome = validate_built_evidence(warning)
    valid_outcome = validate_built_evidence(valid)
    assert "evidence_warning_detected" in _kinds(warning_outcome)
    assert "evidence_validation_completed" in _kinds(valid_outcome)
