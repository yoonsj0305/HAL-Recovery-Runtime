import json

import pytest

from hal_runtime.adapter_simulator import (
    load_runtime_plan,
    simulate_plan,
    simulate_plan_file,
)
from hal_runtime.cli import EXIT_INVALID, main


@pytest.mark.parametrize(
    ("sample", "expected_status", "reason_field", "reason"),
    [
        (
            "samples/runtime_plan_missing_plan_status.json",
            "invalid_plan",
            "adapter_validation_reasons",
            "missing_required_field:plan_status",
        ),
        (
            "samples/runtime_plan_actions_not_list.json",
            "invalid_plan",
            "adapter_validation_reasons",
            "actions_must_be_list",
        ),
        (
            "samples/runtime_plan_wrong_claim_boundary.json",
            "blocked_safety_boundary",
            "adapter_safety_failure_reasons",
            "claim_boundary_must_be_simulation_only_not_certified",
        ),
        (
            "samples/runtime_plan_wrong_execution_mode.json",
            "blocked_safety_boundary",
            "adapter_safety_failure_reasons",
            "execution_mode_must_be_dry_run",
        ),
        (
            "samples/runtime_plan_unsafe_hardware_enabled.json",
            "blocked_safety_boundary",
            "adapter_safety_failure_reasons",
            "hardware_control_enabled_must_be_false",
        ),
    ],
)
def test_invalid_and_unsafe_plan_reasons_are_separated(
    sample, expected_status, reason_field, reason
):
    report = simulate_plan(load_runtime_plan(sample)).report.to_dict()

    assert report["adapter_simulation_status"] == expected_status
    assert reason in report[reason_field]
    assert report["simulated_actions"] == 0


def test_invalid_plan_exits_nonzero_through_cli(tmp_path):
    result = main(
        [
            "simulate-plan",
            "samples/runtime_plan_missing_plan_status.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = json.loads((tmp_path / "adapter_report.json").read_text(encoding="utf-8"))
    assert result == EXIT_INVALID
    assert report["adapter_simulation_status"] == "invalid_plan"


def test_invalid_json_stops_at_plan_load(tmp_path):
    plan_path = tmp_path / "invalid.json"
    output = tmp_path / "output"
    plan_path.write_text("{bad", encoding="utf-8")

    outcome = simulate_plan_file(plan_path, output)

    assert outcome.report.adapter_execution_stage == "plan_load"
    assert outcome.report.adapter_validation_reasons == ("invalid_json",)
    assert outcome.report.plan_loaded is False

