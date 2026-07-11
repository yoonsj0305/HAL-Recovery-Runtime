from hal_runtime.evidence_bundle_builder import build_evidence_bundle
from hal_runtime.evidence_validator import validate_built_evidence


def test_missing_required_source_reason(tmp_path):
    outcome = build_evidence_bundle(
        "samples/evidence_input_missing_required", tmp_path
    )
    assert outcome.report["evidence_validation_status"] == "invalid_missing_required_artifacts"
    assert "missing_required_artifact:policy_decision.json" in outcome.report[
        "evidence_validation_reasons"
    ]


def test_missing_copied_artifact_reason():
    report = validate_built_evidence(
        "samples/evidence_bundle_missing_copied_artifact"
    ).report
    assert report["evidence_validation_status"] == "invalid_missing_copied_artifacts"
    assert "missing_copied_artifact:runtime_report.json" in report[
        "evidence_validation_reasons"
    ]


def test_missing_manifest_entry_reason():
    report = validate_built_evidence(
        "samples/evidence_bundle_missing_manifest_entry"
    ).report
    assert report["evidence_validation_status"] == "invalid_missing_manifest_entries"
    assert "missing_manifest_entry:policy_report.json" in report[
        "evidence_validation_reasons"
    ]
