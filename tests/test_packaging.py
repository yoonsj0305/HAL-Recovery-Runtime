from zipfile import ZipFile

from scripts.package_release import build_release_zip


def test_release_zip_uses_posix_paths_and_excludes_local_state(tmp_path):
    output = build_release_zip(tmp_path / "hal-recovery-runtime-v1.0.0.zip")

    assert output.is_file()
    with ZipFile(output) as archive:
        names = archive.namelist()

    assert names
    assert all("\\" not in name for name in names)
    assert "hal-recovery-runtime/README.md" in names
    assert "hal-recovery-runtime/pyproject.toml" in names
    assert "hal-recovery-runtime/scripts/package_release.py" in names
    assert any(name.startswith("hal-recovery-runtime/samples/") for name in names)
    assert "hal-recovery-runtime/samples/compiler_bundle_valid/recovery_profile.json" in names
    assert (
        "hal-recovery-runtime/samples/compiler_bundle_missing_solver_report/functional_passport.json"
        in names
    )
    assert "hal-recovery-runtime/samples/runtime_plan_valid.json" in names
    assert "hal-recovery-runtime/samples/runtime_plan_missing_plan_status.json" in names
    assert "hal-recovery-runtime/samples/failure_scenario_partial_plan_failure.json" in names
    assert (
        "hal-recovery-runtime/samples/failure_scenario_adapter_unavailable_after_first_action.json"
        in names
    )
    assert "hal-recovery-runtime/samples/runtime_plan_two_actions.json" in names
    assert "hal-recovery-runtime/samples/policy_config_conservative_default.json" in names
    assert "hal-recovery-runtime/src/hal_runtime/policy_simulator.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/evidence_bundle_builder.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/pipeline_runner.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/pipeline_report.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/pipeline_artifacts.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/shadow_report.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/shadow_validator.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/shadow_readers.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/shadow_quality.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/review_package_builder.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/profile_promoter.py" in names
    assert "hal-recovery-runtime/src/hal_runtime/review_validator.py" in names
    assert "hal-recovery-runtime/samples/pipeline_profile_two_actions.json" in names
    assert "hal-recovery-runtime/samples/evidence_input_valid/runtime_plan.json" in names
    assert "hal-recovery-runtime/samples/shadow_input_valid/test_log.csv" in names
    assert "hal-recovery-runtime/samples/shadow_input_valid/tile_status.json" in names
    assert "hal-recovery-runtime/samples/shadow_input_unsafe_field/test_log.json" in names
    assert "hal-recovery-runtime/samples/shadow_input_quality_mixed/test_log.csv" in names
    assert "hal-recovery-runtime/samples/shadow_input_conflict_multi/test_log.csv" in names
    assert "hal-recovery-runtime/samples/review_decision_approved.json" in names
    assert "hal-recovery-runtime/samples/review_decision_wrong_scope_hardware.json" in names
    assert "hal-recovery-runtime/tests/test_evidence_cli.py" in names
    assert "hal-recovery-runtime/tests/test_shadow_ingestion_cli.py" in names
    assert "hal-recovery-runtime/tests/test_shadow_validation_cli.py" in names
    assert "hal-recovery-runtime/tests/test_shadow_quality_report.py" in names
    assert "hal-recovery-runtime/tests/test_shadow_validation_matrix.py" in names
    assert "hal-recovery-runtime/tests/test_candidate_review_builder.py" in names
    assert "hal-recovery-runtime/tests/test_profile_promotion.py" in names
    assert "hal-recovery-runtime/tests/test_reviewed_profile_runtime_compat.py" in names
    assert "hal-recovery-runtime/samples/evidence_input_invalid_json/runtime_plan.json" in names
    assert "hal-recovery-runtime/samples/evidence_bundle_hash_mismatch/evidence_manifest.json" in names
    assert "hal-recovery-runtime/tests/test_evidence_validation_semantics.py" in names
    assert "hal-recovery-runtime/tests/test_pipeline_cli.py" in names
    assert "hal-recovery-runtime/tests/test_pipeline_report_semantics.py" in names
    assert "hal-recovery-runtime/tests/test_pipeline_trace_semantics_v071.py" in names
    assert any(name.startswith("hal-recovery-runtime/src/") for name in names)
    assert any(name.startswith("hal-recovery-runtime/tests/") for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(".pytest_cache" in name for name in names)
    assert not any(".venv" in name for name in names)
    assert not any(".egg-info" in name for name in names)
    assert not any("/dist/" in name for name in names)
