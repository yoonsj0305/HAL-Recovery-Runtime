import pytest

from hal_runtime.evidence_bundle_builder import build_evidence_bundle


@pytest.mark.parametrize(("sample", "status", "passed"), [
    ("evidence_input_valid", "valid_evidence_bundle", True),
    ("evidence_input_missing_required", "invalid_missing_required_artifacts", False),
    ("evidence_input_policy_mismatch", "invalid_policy_decision_mismatch", False),
    ("evidence_input_unsafe_policy", "blocked_safety_boundary", False),
    ("evidence_input_profile_mismatch", "invalid_profile_id_mismatch", False),
])
def test_builder_statuses(sample, status, passed, tmp_path):
    outcome = build_evidence_bundle(f"samples/{sample}", tmp_path)
    assert outcome.report["evidence_validation_status"] == status
    assert outcome.report["evidence_validation_passed"] is passed
    assert {path.name for path in tmp_path.iterdir()} == {
        "artifacts", "evidence_manifest.json", "evidence_bundle.json",
        "evidence_report.json", "evidence_trace.jsonl",
    }


def test_optional_artifacts_do_not_hard_fail(tmp_path):
    outcome = build_evidence_bundle(
        "samples/evidence_input_version_mismatch_warning", tmp_path
    )
    assert outcome.report["evidence_validation_passed"] is True
    assert outcome.report["evidence_validation_status"] == "valid_with_warnings"
    assert "version_mismatch:runtime_plan.json" in outcome.report[
        "evidence_warning_reasons"
    ]
