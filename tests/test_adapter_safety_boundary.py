from pathlib import Path

from hal_runtime.adapter_simulator import load_runtime_plan, simulate_plan


FORBIDDEN_SOURCE_STRINGS = (
    "pyserial",
    "serial.Serial",
    "socket.socket",
    "RPi.GPIO",
    "smbus",
    "pyvisa",
    "hid.device",
    "usb.core",
    "ctypes.CDLL",
    "mmap.mmap",
    "subprocess.run",
    "subprocess.Popen",
    "firmware_flash",
    "voltage_set",
    "timing_set",
    "memory_controller_write",
    "hardware_command",
    "device_command",
    "real_rollback",
    "apply_rollback",
)


def test_runtime_source_has_no_forbidden_hardware_imports_or_calls():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/hal_runtime").glob("*.py")
    )

    assert all(forbidden not in source for forbidden in FORBIDDEN_SOURCE_STRINGS)


def test_adapter_result_has_no_command_fields_and_declares_limitations():
    outcome = simulate_plan(load_runtime_plan("samples/runtime_plan_valid.json"))
    report = outcome.report.to_dict()

    assert "no_real_hardware_control" in report["known_limitations"]
    assert all("command" not in key for result in report["adapter_results"] for key in result)


def test_unsafe_plan_never_creates_simulated_actions():
    outcome = simulate_plan(
        load_runtime_plan("samples/runtime_plan_unsafe_hardware_enabled.json")
    )

    assert outcome.report.adapter_simulation_status == "blocked_safety_boundary"
    assert outcome.report.simulated_actions == 0
    assert outcome.report.adapter_results == ()
