from copy import deepcopy

from hal_runtime.compatibility import check_compatibility
from hal_runtime.profile_loader import load_profile


def test_valid_profile_is_compatible():
    result = check_compatibility(load_profile("samples/recovery_profile.json"))

    assert result.runtime_version == "1.0.0"
    assert result.compatible is True
    assert result.missing_fields == ()
    assert result.unsupported_fields == ()
    assert result.warnings == ()


def test_missing_unassigned_workloads_is_incompatible():
    result = check_compatibility(
        load_profile("samples/unsafe_missing_unassigned_workloads_profile.json")
    )

    assert result.compatible is False
    assert "unassigned_workloads" in result.missing_fields


def test_suspicious_action_like_field_warns_without_incompatibility():
    profile = load_profile("samples/recovery_profile.json")
    profile["hardware_actions"] = []

    result = check_compatibility(profile)

    assert result.compatible is True
    assert result.unsupported_fields == ("hardware_actions",)
    assert result.warnings == (
        "unsupported_action_like_field_detected:hardware_actions",
    )


def test_compatibility_check_does_not_mutate_profile():
    profile = load_profile("samples/unknown_action_profile.json")
    original = deepcopy(profile)

    check_compatibility(profile)

    assert profile == original
