from hal_runtime.adapter_simulator import load_runtime_plan, simulate_plan


REQUIRED_REPORT_FIELDS = {
    "runtime_version",
    "adapter_layer_version",
    "simulation_only",
    "hardware_control_enabled",
    "claim_boundary",
    "plan_loaded",
    "plan_status",
    "adapter_simulation_status",
    "adapter_execution_stage",
    "adapter_block_reasons",
    "adapter_safety_failure_reasons",
    "adapter_validation_reasons",
    "source_plan_summary",
    "adapter_result_summary",
    "available_adapters",
    "simulated_actions",
    "blocked_actions",
    "skipped_actions",
    "adapter_results",
    "known_limitations",
}


def test_adapter_report_schema_is_stable_for_valid_plan():
    report = simulate_plan(
        load_runtime_plan("samples/runtime_plan_valid.json")
    ).report.to_dict()

    assert REQUIRED_REPORT_FIELDS <= report.keys()
    assert report["runtime_version"] == "1.0.0"
    assert report["adapter_layer_version"] == "1.0.0"
    assert report["adapter_execution_stage"] == "adapter_simulation_completed"
    assert report["adapter_block_reasons"] == []
    assert report["adapter_safety_failure_reasons"] == []
    assert report["adapter_validation_reasons"] == []


def test_source_plan_summary_contains_only_bounded_metadata():
    report = simulate_plan(
        load_runtime_plan("samples/runtime_plan_valid.json")
    ).report.to_dict()
    summary = report["source_plan_summary"]

    assert set(summary) == {
        "runtime_version",
        "profile_id",
        "execution_mode",
        "plan_status",
        "planned_action_count",
        "blocked_action_count",
        "plan_block_reasons",
    }
    assert summary["planned_action_count"] == 1
    assert summary["blocked_action_count"] == 0
    assert "actions" not in summary


def test_result_summary_matches_adapter_results():
    report = simulate_plan(
        load_runtime_plan("samples/runtime_plan_with_unknown_action.json")
    ).report.to_dict()
    summary = report["adapter_result_summary"]

    assert summary["simulated"] == 0
    assert summary["blocked_unsupported_action"] == 1
    assert sum(summary.values()) == len(report["adapter_results"])


def test_skipped_summary_reflects_skipped_action_count():
    plan = load_runtime_plan("samples/runtime_plan_blocked_by_safety_gate.json")
    plan["actions"] = [
        {
            "action_id": "ACT_SKIPPED",
            "action_type": "assign_workload",
            "role": "sensor_tile",
        }
    ]

    report = simulate_plan(plan).report.to_dict()

    assert report["skipped_actions"] == 1
    assert report["adapter_result_summary"]["skipped_plan_not_executable"] == 1
    assert report["adapter_results"] == []
