import json
from copy import deepcopy

import pytest

from hal_runtime.policy_config import validate_policy_config


def _config():
    return json.loads(open("samples/policy_config_conservative_default.json", encoding="utf-8").read())


def test_valid_conservative_config_passes_without_mutation():
    config = _config()
    original = deepcopy(config)
    result = validate_policy_config(config)
    assert result.structurally_valid and result.safety_boundary_passed
    assert config == original


@pytest.mark.parametrize(("field", "reason"), [
    ("allow_real_execution", "allow_real_execution_must_be_false"),
    ("allow_hardware_control", "allow_hardware_control_must_be_false"),
    ("allow_retry", "allow_retry_must_be_false"),
])
def test_forbidden_permission_is_rejected(field, reason):
    config = _config()
    config[field] = True
    assert reason in validate_policy_config(config).safety_reasons


def test_wrong_claim_and_unsupported_mode_fail():
    config = _config()
    config["claim_boundary"] = "unbounded"
    assert "claim_boundary_must_be_simulation_only_not_certified" in validate_policy_config(config).safety_reasons
    config = _config()
    config["policy_mode"] = "unknown"
    assert "unsupported_policy_mode:unknown" in validate_policy_config(config).structural_reasons
