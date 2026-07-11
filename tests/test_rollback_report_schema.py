from hal_runtime.rollback_simulator import simulate_failure_file


REQUIRED = {
    "runtime_version", "rollback_simulation_version", "simulation_only",
    "hardware_control_enabled", "claim_boundary", "plan_loaded", "scenario_loaded",
    "source_plan_summary", "scenario_summary", "rollback_simulation_status",
    "injected_failure_mode", "simulated_actions_before_failure", "failed_actions",
    "skipped_actions", "rollback_required", "rollback_actions_planned",
    "rollback_strategy", "failure_reasons", "rollback_reasons", "known_limitations",
    "rollback_semantics_version", "safe_stop_required", "no_action_taken",
    "simulated_revert_actions_planned", "safe_stop_markers_planned",
    "skip_markers_planned", "no_action_markers_planned",
}


def test_rollback_report_schema_is_stable(tmp_path):
    outcome = simulate_failure_file("samples/runtime_plan_valid.json", tmp_path)
    payload = outcome.rollback_report.to_dict()
    assert REQUIRED <= payload.keys()
    assert payload["runtime_version"] == "1.0.0"
    assert payload["rollback_simulation_version"] == "1.0.0"
    assert payload["rollback_semantics_version"] == "1.0.0"
    assert payload["simulation_only"] is True
    assert payload["hardware_control_enabled"] is False
