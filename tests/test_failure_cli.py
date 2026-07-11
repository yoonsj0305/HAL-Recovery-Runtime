import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _report(path):
    return json.loads((path / "rollback_report.json").read_text(encoding="utf-8"))


def test_no_failure_cli_writes_all_artifacts(tmp_path):
    result = main(["simulate-failure", "samples/runtime_plan_valid.json", "--out", str(tmp_path)])
    assert result == EXIT_OK
    assert {p.name for p in tmp_path.iterdir()} == {
        "failure_trace.jsonl", "rollback_plan.json", "rollback_report.json"
    }
    assert _report(tmp_path)["rollback_simulation_status"] == "rollback_not_required"


def test_partial_failure_cli_generates_rollback(tmp_path):
    result = main([
        "simulate-failure", "samples/runtime_plan_two_actions.json",
        "--scenario", "samples/failure_scenario_partial_plan_failure.json",
        "--out", str(tmp_path),
    ])
    assert result == EXIT_OK
    assert _report(tmp_path)["rollback_simulation_status"] == "rollback_plan_generated"


def test_blocking_inputs_exit_nonzero(tmp_path):
    cases = [
        ("samples/runtime_plan_valid.json", "samples/failure_scenario_unsafe_hardware_enabled.json"),
        ("samples/runtime_plan_valid.json", "samples/failure_scenario_unsupported_mode.json"),
        ("samples/runtime_plan_unsafe_hardware_enabled.json", None),
    ]
    for index, (plan, scenario) in enumerate(cases):
        output = tmp_path / str(index)
        args = ["simulate-failure", plan, "--out", str(output)]
        if scenario:
            args[2:2] = ["--scenario", scenario]
        assert main(args) == EXIT_INVALID

