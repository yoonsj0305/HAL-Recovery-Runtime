import json

from hal_runtime.cli import EXIT_OK, main
from hal_runtime.failure_modes import FAILURE_MODES


def test_required_failure_modes_are_built_in():
    names = {mode.failure_mode for mode in FAILURE_MODES}
    assert names == {
        "none",
        "adapter_unavailable",
        "action_timeout",
        "route_unavailable",
        "unsupported_role_after_injection",
        "partial_plan_failure",
        "forced_safety_boundary_failure",
    }
    assert all(mode.rollback_strategy for mode in FAILURE_MODES)


def test_list_failure_modes_cli_and_output(tmp_path):
    assert main(["list-failure-modes", "--out", str(tmp_path)]) == EXIT_OK
    payload = json.loads((tmp_path / "failure_modes.json").read_text(encoding="utf-8"))
    assert payload["runtime_version"] == "1.0.0"
    assert payload["simulation_only"] is True
    assert len(payload["failure_modes"]) == 7
