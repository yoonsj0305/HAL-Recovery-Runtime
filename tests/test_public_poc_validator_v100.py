import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main
from hal_runtime.public_poc_validator import validate_public_poc


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_public_poc_validator_runs_full_internal_workflow(tmp_path):
    report, validation = validate_public_poc(tmp_path)
    assert report["public_poc_passed"] is True
    assert report["public_poc_status"] == "public_poc_completed"
    assert report["profile_id"] == "PUBLIC_POC_PROFILE_001"
    assert report["candidate_tile_count"] == 4
    assert report["final_selected_policy"] == "human_review_required"
    assert report["review_decision_explicit"] is True
    assert report["promotion_scope"] == "dry_run_only"
    assert validation["validation_passed"] is True
    assert validation["validation_status"] == "valid_public_poc"
    assert all(item["passed"] for item in validation["validation_matrix"].values())
    profile = _read(tmp_path / "workspace" / "promoted" / "reviewed_recovery_profile.json")
    assert profile["hardware_control_enabled"] is False
    assert profile["hardware_execution_enabled"] is False
    assert profile["profile_origin"]["lineage_hashes_present"] is True
    events = [json.loads(line)["event_type"] for line in (tmp_path / "public_poc_trace.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {
        "public_poc_validation_started",
        "release_contract_validated",
        "public_poc_review_decision_validated",
        "public_poc_promotion_lineage_validated",
        "public_poc_dry_run_validated",
        "public_poc_safety_invariants_validated",
        "public_poc_validation_completed",
    } <= set(events)


def test_validate_public_poc_cli_and_invalid_example(tmp_path):
    valid = tmp_path / "valid"
    invalid = tmp_path / "invalid"
    empty_example = tmp_path / "empty-example"
    empty_example.mkdir()
    assert main(["validate-public-poc", "--out", str(valid)]) == EXIT_OK
    assert main(["validate-public-poc", "--example-root", str(empty_example), "--out", str(invalid)]) == EXIT_INVALID
    invalid_report = _read(invalid / "public_poc_validation_report.json")
    assert invalid_report["validation_status"] == "invalid_example_inputs"
    assert invalid_report["validation_passed"] is False


def test_public_poc_validator_contains_no_shell_orchestration_calls():
    source = open("src/hal_runtime/public_poc_validator.py", encoding="utf-8").read()
    forbidden = ("subprocess" + ".run", "subprocess" + ".Popen", "os" + ".system")
    assert not [item for item in forbidden if item in source]

