from copy import deepcopy

from hal_runtime.failure_models import validate_failure_scenario
from hal_runtime.failure_modes import supported_failure_modes


def _valid():
    return {
        "scenario_id": "S1",
        "failure_mode": "none",
        "injection_stage": "adapter_simulation",
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": "simulation_only_not_certified",
    }


def test_valid_scenario_passes_without_mutation():
    scenario = _valid()
    original = deepcopy(scenario)
    result = validate_failure_scenario(scenario, supported_failure_modes())
    assert result.valid is True
    assert scenario == original


def test_scenario_validation_reasons():
    cases = [
        ({**_valid(), "hardware_control_enabled": True}, "hardware_control_enabled_must_be_false"),
        ({**_valid(), "failure_mode": "bad"}, "unsupported_failure_mode:bad"),
        ({k: v for k, v in _valid().items() if k != "scenario_id"}, "missing_required_field:scenario_id"),
        ({**_valid(), "claim_boundary": "wrong"}, "claim_boundary_must_be_simulation_only_not_certified"),
    ]
    for scenario, reason in cases:
        result = validate_failure_scenario(scenario, supported_failure_modes())
        assert result.valid is False
        assert reason in result.reasons

