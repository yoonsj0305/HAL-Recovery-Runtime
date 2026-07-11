from pathlib import Path

from hal_runtime.cli import EXIT_INVALID, main
from hal_runtime.policy_simulator import simulate_policy_file


def test_permissions_remain_false_for_valid_and_blocked_outputs(tmp_path):
    for name, plan in (("valid", "samples/runtime_plan_valid.json"), ("unsafe", "samples/runtime_plan_unsafe_hardware_enabled.json")):
        outcome = simulate_policy_file(plan, tmp_path / name)
        assert outcome.decision.real_execution_allowed is False
        assert outcome.decision.hardware_control_allowed is False
        assert outcome.decision.retry_allowed is False
        assert outcome.decision.selected_policy not in {"real_execute", "firmware_update", "driver_apply"}


def test_unsafe_inputs_block_before_approval(tmp_path):
    assert main(["simulate-policy", "samples/runtime_plan_unsafe_hardware_enabled.json", "--out", str(tmp_path / "plan")]) == EXIT_INVALID
    assert main(["simulate-policy", "samples/runtime_plan_valid.json", "--policy-config", "samples/policy_config_unsafe_hardware_control.json", "--out", str(tmp_path / "config")]) == EXIT_INVALID


def test_static_forbidden_guard_scans_runtime_source_only():
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/hal_runtime").glob("*.py"))
    forbidden = (
        "pyserial", "serial.Serial", "socket.socket", "RPi.GPIO", "smbus", "pyvisa",
        "hid.device", "usb.core", "ctypes.CDLL", "mmap.mmap", "subprocess.run",
        "subprocess.Popen", "firmware_flash", "voltage_set", "timing_set",
        "memory_controller_write", "hardware_command", "device_command", "real_rollback",
        "apply_rollback", "hardware_execute", "real_policy_enforcement", "apply_to_device",
    )
    assert not [item for item in forbidden if item in source]
