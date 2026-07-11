from pathlib import Path

from hal_runtime.rollback_simulator import simulate_failure_file


def test_unsafe_plan_and_scenario_block_before_injection(tmp_path):
    unsafe_plan = simulate_failure_file(
        "samples/runtime_plan_unsafe_hardware_enabled.json", tmp_path / "plan"
    )
    unsafe_scenario = simulate_failure_file(
        "samples/runtime_plan_valid.json", tmp_path / "scenario",
        "samples/failure_scenario_unsafe_hardware_enabled.json",
    )
    assert unsafe_plan.rollback_report.rollback_simulation_status == "blocked_plan_safety_boundary"
    assert unsafe_scenario.rollback_report.rollback_simulation_status == "blocked_scenario_safety_boundary"
    assert unsafe_plan.rollback_report.simulated_actions_before_failure == 0
    assert unsafe_scenario.rollback_report.simulated_actions_before_failure == 0


def test_outputs_make_no_physical_recovery_claims(tmp_path):
    outcome = simulate_failure_file(
        "samples/runtime_plan_two_actions.json", tmp_path,
        "samples/failure_scenario_partial_plan_failure.json",
    )
    plan = outcome.rollback_plan.to_dict()
    report = outcome.rollback_report.to_dict()
    assert report["simulation_only"] is True
    assert report["hardware_control_enabled"] is False
    assert all("command" not in key for action in plan["rollback_actions"] for key in action)


def test_extended_forbidden_source_guard():
    forbidden = (
        "pyserial", "serial.Serial", "socket.socket", "RPi.GPIO", "smbus", "pyvisa",
        "hid.device", "usb.core", "ctypes.CDLL", "mmap.mmap", "subprocess.run",
        "subprocess.Popen", "firmware_flash", "voltage_set", "timing_set",
        "memory_controller_write", "hardware_command", "device_command",
        "real_rollback", "apply_rollback",
    )
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in Path("src/hal_runtime").glob("*.py")
    )
    assert all(value not in source for value in forbidden)

