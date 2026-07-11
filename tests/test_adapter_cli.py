import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _report(path):
    return json.loads((path / "adapter_report.json").read_text(encoding="utf-8"))


def test_simulate_valid_plan_writes_trace_and_report(tmp_path):
    result = main(
        ["simulate-plan", "samples/runtime_plan_valid.json", "--out", str(tmp_path)]
    )

    report = _report(tmp_path)
    assert result == EXIT_OK
    assert (tmp_path / "adapter_trace.jsonl").is_file()
    assert report["runtime_version"] == "1.0.0"
    assert report["adapter_simulation_status"] == "adapter_simulation_passed"
    assert report["simulation_only"] is True
    assert report["hardware_control_enabled"] is False
    assert report["claim_boundary"] == "simulation_only_not_certified"


def test_unknown_action_completes_with_blocks(tmp_path):
    result = main(
        [
            "simulate-plan",
            "samples/runtime_plan_with_unknown_action.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _report(tmp_path)
    assert result == EXIT_OK
    assert report["adapter_simulation_status"] == "adapter_simulation_completed_with_blocks"
    assert report["adapter_results"][0]["simulation_status"] == "blocked_unsupported_action"


def test_blocked_plan_exits_zero_and_is_skipped(tmp_path):
    result = main(
        [
            "simulate-plan",
            "samples/runtime_plan_blocked_by_safety_gate.json",
            "--out",
            str(tmp_path),
        ]
    )

    assert result == EXIT_OK
    assert _report(tmp_path)["adapter_simulation_status"] == "skipped_plan_not_executable"


def test_unsafe_plan_exits_nonzero_and_is_blocked(tmp_path):
    result = main(
        [
            "simulate-plan",
            "samples/runtime_plan_unsafe_hardware_enabled.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _report(tmp_path)
    assert result == EXIT_INVALID
    assert report["adapter_simulation_status"] == "blocked_safety_boundary"
    assert report["simulated_actions"] == 0


def test_list_adapters_writes_registry_when_out_is_given(tmp_path):
    result = main(["list-adapters", "--out", str(tmp_path)])

    registry = json.loads(
        (tmp_path / "adapter_registry.json").read_text(encoding="utf-8")
    )
    assert result == EXIT_OK
    assert registry["runtime_version"] == "1.0.0"
    assert registry["simulation_only"] is True
    assert registry["hardware_control_enabled"] is False
    assert len(registry["adapters"]) >= 3
