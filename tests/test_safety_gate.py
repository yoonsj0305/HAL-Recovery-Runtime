from copy import deepcopy

import pytest

from hal_runtime.profile_loader import load_profile
from hal_runtime.safety_gate import SafetyGate


@pytest.fixture
def valid_profile():
    return load_profile("samples/recovery_profile.json")


def test_valid_profile_passes(valid_profile):
    result = SafetyGate().evaluate(valid_profile)

    assert result.passed is True
    assert result.degraded_mode is False
    assert result.failure_reasons == ()
    assert valid_profile["unassigned_workloads"] == []


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("hardware_control_enabled", True, "hardware_control_enabled_must_be_false"),
        ("human_review_required", False, "human_review_required_must_be_true"),
        ("claim_boundary", "other", "claim_boundary_must_be_simulation_only_not_certified"),
        ("voltage_policy", "other", "voltage_policy_must_be_no_hardware_control"),
        ("runtime_loader_hint", "other", "runtime_loader_hint_must_be_simulation_only"),
    ],
)
def test_wrong_safety_value_fails(valid_profile, field, value, reason):
    profile = deepcopy(valid_profile)
    profile[field] = value

    result = SafetyGate().evaluate(profile)

    assert result.passed is False
    assert reason in result.failure_reasons


def test_missing_claim_boundary_fails(valid_profile):
    profile = deepcopy(valid_profile)
    profile.pop("claim_boundary")

    result = SafetyGate().evaluate(profile)

    assert result.passed is False
    assert "claim_boundary_must_be_simulation_only_not_certified" in result.failure_reasons


@pytest.mark.parametrize("field", ["assigned_workloads", "blocked_roles", "allowed_roles"])
def test_required_planning_field_checked(valid_profile, field):
    profile = deepcopy(valid_profile)
    profile.pop(field)

    result = SafetyGate().evaluate(profile)

    assert result.passed is False
    assert f"{field}_is_required" in result.failure_reasons


def test_missing_routes_enters_degraded_mode(valid_profile):
    profile = deepcopy(valid_profile)
    profile.pop("preferred_routes")

    result = SafetyGate().evaluate(profile)

    assert result.passed is True
    assert result.degraded_mode is True
    assert result.warnings == ("preferred_routes_missing",)


def test_missing_unassigned_workloads_fails_with_contract_reason(valid_profile):
    profile = deepcopy(valid_profile)
    profile.pop("unassigned_workloads")

    result = SafetyGate().evaluate(profile)

    assert result.passed is False
    assert "missing_unassigned_workloads" in result.failure_reasons


def test_unassigned_workloads_must_be_list(valid_profile):
    profile = deepcopy(valid_profile)
    profile["unassigned_workloads"] = "WL_UNASSIGNED"

    result = SafetyGate().evaluate(profile)

    assert result.passed is False
    assert "unassigned_workloads_must_be_list" in result.failure_reasons


def test_empty_unassigned_workloads_list_passes(valid_profile):
    profile = deepcopy(valid_profile)
    profile["unassigned_workloads"] = []

    result = SafetyGate().evaluate(profile)

    assert result.passed is True


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("hardware_control_enabled", 0, "hardware_control_enabled_must_be_false"),
        ("human_review_required", 1, "human_review_required_must_be_true"),
    ],
)
def test_boolean_boundaries_reject_numeric_lookalikes(valid_profile, field, value, reason):
    profile = deepcopy(valid_profile)
    profile[field] = value

    result = SafetyGate().evaluate(profile)

    assert result.passed is False
    assert reason in result.failure_reasons
