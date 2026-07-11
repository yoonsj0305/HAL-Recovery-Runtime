from pathlib import Path

from hal_runtime.evidence_bundle_builder import build_evidence_bundle


def test_evidence_outputs_remain_non_certifying_and_non_controlling(tmp_path):
    outcome = build_evidence_bundle("samples/evidence_input_valid", tmp_path)
    assert outcome.bundle["simulation_only"] is True
    assert outcome.bundle["hardware_control_enabled"] is False
    assert outcome.bundle["safety_summary"]["real_execution_allowed_anywhere"] is False
    assert outcome.bundle["safety_summary"]["policy_allows_hardware_control"] is False
    assert "not_certified" in outcome.bundle["known_limitations"]


def test_static_forbidden_evidence_guard():
    source = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/hal_runtime").glob("*.py"))
    forbidden = (
        "pyserial", "serial.Serial", "socket.socket", "RPi.GPIO", "smbus", "pyvisa",
        "hid.device", "usb.core", "ctypes.CDLL", "mmap.mmap", "subprocess.run",
        "subprocess.Popen", "firmware_flash", "voltage_set", "timing_set",
        "memory_controller_write", "hardware_command", "device_command", "real_rollback",
        "apply_rollback", "real_policy_enforcement", "hardware_execute", "apply_to_device",
        "certified_runtime", "certified_recovery",
    )
    assert not [item for item in forbidden if item in source]
