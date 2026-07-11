import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_candidate_safety_invariants_v081(tmp_path):
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(tmp_path)]) == EXIT_OK

    candidate = _read(tmp_path / "recovery_profile_candidate.json")
    summary = candidate["candidate_confidence_summary"]

    assert candidate["human_review_required"] is True
    assert candidate["hardware_execution_enabled"] is False
    assert candidate["hardware_control_enabled"] is False
    assert candidate["voltage_policy"] == "no_hardware_control"
    assert candidate["runtime_loader_hint"] == "simulation_only"
    assert candidate["assigned_workloads"] == []
    assert summary["safe_for_pipeline_handoff"] is False


def test_shadow_candidate_assigned_workloads_invalidates_v081(tmp_path):
    source = tmp_path / "shadow"
    validation = tmp_path / "validation"
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(source)]) == EXIT_OK
    candidate_path = source / "recovery_profile_candidate.json"
    candidate = _read(candidate_path)
    candidate["assigned_workloads"] = [{"workload_id": "W1"}]
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

    assert main(["validate-shadow-data", str(source), "--out", str(validation)]) == EXIT_INVALID
    assert "candidate_assigned_workloads_not_allowed_v1_0_0" in _read(
        validation / "shadow_validation_report.json"
    )["validation_reasons"]
