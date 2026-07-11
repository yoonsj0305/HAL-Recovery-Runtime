import json

from hal_runtime.cli import EXIT_OK, main
from hal_runtime.policy_rules import POLICY_MODES, supported_policy_modes


EXPECTED = {
    "conservative_default", "safe_stop_first", "rollback_if_prior_actions",
    "no_retry_v0_5_0", "degraded_requires_review", "no_action_on_boundary_failure",
}


def test_required_policy_modes_are_fixed_and_non_executing():
    assert supported_policy_modes() == EXPECTED
    assert all(mode.real_execution_allowed is False for mode in POLICY_MODES)


def test_list_policies_cli_and_artifact(tmp_path):
    assert main(["list-policies"]) == EXIT_OK
    assert main(["list-policies", "--out", str(tmp_path)]) == EXIT_OK
    payload = json.loads((tmp_path / "policy_modes.json").read_text(encoding="utf-8"))
    assert payload["runtime_version"] == "1.0.0"
    assert payload["simulation_only"] is True
    assert payload["hardware_control_enabled"] is False
    assert {item["policy_mode"] for item in payload["policy_modes"]} == EXPECTED
