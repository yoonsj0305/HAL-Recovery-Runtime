import json

from hal_runtime.dry_run_executor import run_bundle_dry_run, run_dry_run


SINGLE_REPORT_FIELDS = {
    "runtime_version",
    "execution_mode",
    "profile_loaded",
    "safety_gate_evaluated",
    "safety_gate_passed",
    "bundle_gate_evaluated",
    "bundle_mode",
    "execution_gate_stage",
    "planned_actions",
    "blocked_actions",
    "degraded_mode_entered",
    "runtime_status",
    "safety_failure_reasons",
    "degraded_mode_reasons",
}

BUNDLE_REPORT_FIELDS = {
    "bundle_validation_passed",
    "bundle_validation_status",
    "bundle_validation_reasons",
    "bundle_validation_warnings",
    "present_artifacts",
    "missing_artifacts",
    "degraded_bundle_mode",
    "supporting_artifact_count",
}


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_single_file_success_report_schema_is_stable(tmp_path):
    run_dry_run("samples/recovery_profile.json", tmp_path)

    report = _read(tmp_path / "runtime_report.json")
    assert SINGLE_REPORT_FIELDS <= report.keys()
    assert report["safety_gate_evaluated"] is True
    assert report["bundle_gate_evaluated"] is False


def test_bundle_success_report_schema_is_stable(tmp_path):
    run_bundle_dry_run("samples/compiler_bundle_valid", tmp_path)

    report = _read(tmp_path / "runtime_report.json")
    assert SINGLE_REPORT_FIELDS | BUNDLE_REPORT_FIELDS <= report.keys()
    assert report["safety_gate_evaluated"] is True
    assert report["bundle_gate_evaluated"] is True


def test_invalid_bundle_distinguishes_unreached_safety_gate(tmp_path):
    run_bundle_dry_run("samples/compiler_bundle_mismatch_profile_id", tmp_path)

    report = _read(tmp_path / "runtime_report.json")
    plan = _read(tmp_path / "runtime_plan.json")
    assert report["bundle_gate_evaluated"] is True
    assert report["safety_gate_evaluated"] is False
    assert report["safety_gate_passed"] is False
    assert report["execution_gate_stage"] == "bundle_validation_gate"
    assert report["runtime_status"] == "blocked_by_bundle_validation"
    assert report["planned_actions"] == 0
    assert plan["plan_status"] == "blocked_by_bundle_validation"
    assert plan["actions"] == []
    assert plan["plan_block_reasons"]


def test_safety_failure_report_and_plan_are_auditable(tmp_path):
    run_dry_run("samples/unsafe_hardware_enabled_profile.json", tmp_path)

    report = _read(tmp_path / "runtime_report.json")
    plan = _read(tmp_path / "runtime_plan.json")
    assert report["safety_gate_evaluated"] is True
    assert report["safety_gate_passed"] is False
    assert report["execution_gate_stage"] == "single_file_safety_gate"
    assert report["runtime_status"] == "blocked_by_safety_gate"
    assert report["planned_actions"] == 0
    assert plan["plan_status"] == "blocked_by_safety_gate"
    assert plan["actions"] == []
    assert plan["plan_block_reasons"] == [
        "hardware_control_enabled_must_be_false"
    ]

