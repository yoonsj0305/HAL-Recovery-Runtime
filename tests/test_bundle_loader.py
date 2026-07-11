import json
from copy import deepcopy

import pytest

from hal_runtime.bundle_loader import BundleLoadError, load_compiler_bundle
from hal_runtime.bundle_validator import validate_compiler_bundle


def test_loads_valid_bundle():
    bundle = load_compiler_bundle("samples/compiler_bundle_valid")

    assert bundle.recovery_profile["profile_id"] == "CHIP_001"
    assert len(bundle.present_artifacts) == 5
    assert bundle.missing_artifacts == ()
    assert bundle.load_errors == ()


def test_missing_recovery_profile_is_machine_readable(tmp_path):
    bundle = load_compiler_bundle(tmp_path)

    assert bundle.recovery_profile is None
    assert "recovery_profile.json" in bundle.missing_artifacts
    assert bundle.load_errors == ("recovery_profile_missing",)
    assert validate_compiler_bundle(bundle).bundle_validation_status == "invalid_missing_profile"


def test_invalid_recovery_profile_json_fails_hard(tmp_path):
    (tmp_path / "recovery_profile.json").write_text("{bad", encoding="utf-8")

    with pytest.raises(BundleLoadError, match="recovery_profile_invalid_json"):
        load_compiler_bundle(tmp_path)


def test_missing_optional_artifact_is_reported():
    bundle = load_compiler_bundle("samples/compiler_bundle_missing_solver_report")

    assert "solver_report.json" in bundle.missing_artifacts
    assert bundle.solver_report is None


def test_invalid_optional_json_is_recorded(tmp_path):
    profile = {"profile_id": "P1"}
    (tmp_path / "recovery_profile.json").write_text(json.dumps(profile), encoding="utf-8")
    (tmp_path / "solver_report.json").write_text("[", encoding="utf-8")

    bundle = load_compiler_bundle(tmp_path)

    assert bundle.solver_report is None
    assert "solver_report_invalid_json" in bundle.load_errors
    assert validate_compiler_bundle(bundle).bundle_validation_status == "invalid_artifact_json"


def test_validation_does_not_mutate_loaded_profile():
    bundle = load_compiler_bundle("samples/compiler_bundle_valid")
    original = deepcopy(bundle.recovery_profile)

    validate_compiler_bundle(bundle)

    assert bundle.recovery_profile == original

