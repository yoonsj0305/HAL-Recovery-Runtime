import json

from hal_runtime.cli import EXIT_INVALID, main
from hal_runtime.shadow_validator import validate_shadow_artifacts


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_ingestion_blocks_unsafe_input_fields(tmp_path):
    result = main(
        [
            "ingest-shadow-data",
            "samples/shadow_input_unsafe_field",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "shadow_ingestion_report.json")
    assert result == EXIT_INVALID
    assert report["shadow_ingestion_status"] == "shadow_ingestion_blocked"
    assert report["shadow_validation_status"] == "blocked_safety_boundary"
    assert "hardware_control_enabled_true" in report["safety_boundary_violations"]
    assert "real_execution_allowed_true" in report["safety_boundary_violations"]
    all_output_text = "\n".join(
        path.read_text(encoding="utf-8") for path in tmp_path.iterdir() if path.is_file()
    )
    assert '"hardware_control_enabled": true' not in all_output_text
    assert '"hardware_execution_enabled": true' not in all_output_text
    assert '"certification_passed": true' not in all_output_text
    assert '"safe_for_hardware_control": true' not in all_output_text


def test_shadow_validator_rejects_candidate_that_claims_hardware_control(tmp_path):
    candidate = {
        "runtime_version": "1.0.0",
        "shadow_ingestion_version": "1.0.0",
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": "simulation_only_not_certified",
        "read_only": True,
        "profile_id": "P1",
        "profile_candidate": True,
        "human_review_required": True,
        "hardware_execution_enabled": True,
        "runtime_loader_hint": "simulation_only",
        "voltage_policy": "no_hardware_control",
        "assigned_workloads": [],
    }
    observations = {
        "runtime_version": "1.0.0",
        "shadow_ingestion_version": "1.0.0",
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": "simulation_only_not_certified",
        "read_only": True,
        "profile_id": "P1",
        "observation_count": 0,
        "observations": [],
    }
    report = {
        "runtime_version": "1.0.0",
        "shadow_ingestion_version": "1.0.0",
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": "simulation_only_not_certified",
        "read_only": True,
        "warning_reasons": [],
    }
    quality = {
        **report,
        "shadow_quality_status": "shadow_quality_computed",
        "shadow_quality_score": 0.0,
        "shadow_quality_band": "insufficient",
        "field_coverage": {},
        "conflict_matrix": {"conflict_count": 0, "conflicting_tiles": []},
        "candidate_confidence_summary": {},
        "quality_warning_reasons": [],
        "quality_blocking_reasons": [],
    }
    for payload in (candidate, observations, report, quality):
        payload["shadow_quality_semantics_version"] = "1.0.0"
    (tmp_path / "recovery_profile_candidate.json").write_text(json.dumps(candidate), encoding="utf-8")
    (tmp_path / "shadow_observations.json").write_text(json.dumps(observations), encoding="utf-8")
    (tmp_path / "shadow_ingestion_report.json").write_text(json.dumps(report), encoding="utf-8")
    (tmp_path / "shadow_quality_report.json").write_text(json.dumps(quality), encoding="utf-8")

    validation = validate_shadow_artifacts(tmp_path)

    assert validation["shadow_validation_status"] == "invalid_candidate_profile"
    assert "candidate_hardware_execution_enabled_true" in validation[
        "validation_reasons"
    ]
