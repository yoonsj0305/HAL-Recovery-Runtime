from dataclasses import replace

import pytest

from hal_runtime.bundle_loader import load_compiler_bundle
from hal_runtime.bundle_validator import validate_compiler_bundle


def _valid_bundle():
    return load_compiler_bundle("samples/compiler_bundle_valid")


def test_valid_bundle_passes():
    result = validate_compiler_bundle(_valid_bundle())

    assert result.runtime_version == "1.0.0"
    assert result.bundle_validation_status == "valid_bundle"
    assert result.bundle_validation_passed is True
    assert result.degraded_bundle_mode is False
    assert result.supporting_artifact_count == 4
    assert len(result.present_artifacts) == 5
    assert result.missing_artifacts == ()


def test_missing_solver_degrades_without_failure():
    result = validate_compiler_bundle(
        load_compiler_bundle("samples/compiler_bundle_missing_solver_report")
    )

    assert result.bundle_validation_status == "degraded_missing_artifacts"
    assert result.bundle_validation_passed is True
    assert result.degraded_bundle_mode is True
    assert "solver_report.json" in result.missing_artifacts


def test_profile_id_mismatch_fails():
    result = validate_compiler_bundle(
        load_compiler_bundle("samples/compiler_bundle_mismatch_profile_id")
    )

    assert result.bundle_validation_status == "invalid_profile_id_mismatch"
    assert result.bundle_validation_passed is False
    assert "profile_id_mismatch:solver_report.json" in result.bundle_validation_reasons


def test_artifact_validation_failure_blocks():
    result = validate_compiler_bundle(
        load_compiler_bundle("samples/compiler_bundle_validation_failed")
    )

    assert result.bundle_validation_status == "invalid_artifact_validation_failed"
    assert result.bundle_validation_reasons == ("artifact_validation_failed",)


@pytest.mark.parametrize("solver_status", ["failed", "infeasible"])
def test_failed_solver_status_blocks(solver_status):
    bundle = _valid_bundle()
    solver = {**bundle.solver_report, "solver_status": solver_status}

    result = validate_compiler_bundle(replace(bundle, solver_report=solver))

    assert result.bundle_validation_status == "invalid_solver_failed"
    assert result.bundle_validation_reasons == ("solver_failed",)


def test_degraded_solver_status_degrades():
    bundle = _valid_bundle()
    solver = {**bundle.solver_report, "solver_status": "degraded"}

    result = validate_compiler_bundle(replace(bundle, solver_report=solver))

    assert result.bundle_validation_status == "degraded_solver_status"
    assert result.bundle_validation_passed is True
    assert result.degraded_bundle_mode is True


def test_failed_comparison_blocks():
    bundle = _valid_bundle()
    comparison = {**bundle.comparison_report, "comparison_status": "failed"}

    result = validate_compiler_bundle(replace(bundle, comparison_report=comparison))

    assert result.bundle_validation_status == "invalid_comparison_failed"
    assert result.bundle_validation_reasons == ("comparison_failed",)


@pytest.mark.parametrize(
    "passport_patch",
    [{"passport_status": "failed"}, {"decision_readiness": "not_ready"}],
)
def test_not_ready_passport_blocks(passport_patch):
    bundle = _valid_bundle()
    passport = {**bundle.functional_passport, **passport_patch}

    result = validate_compiler_bundle(replace(bundle, functional_passport=passport))

    assert result.bundle_validation_status == "invalid_passport_not_ready"
    assert result.bundle_validation_reasons == ("functional_passport_not_ready",)


def test_comparison_warnings_are_preserved_without_failure():
    bundle = _valid_bundle()
    comparison = {**bundle.comparison_report, "warnings": ["baseline_gap"]}

    result = validate_compiler_bundle(replace(bundle, comparison_report=comparison))

    assert result.bundle_validation_status == "valid_bundle"
    assert result.bundle_validation_warnings == ("baseline_gap",)
