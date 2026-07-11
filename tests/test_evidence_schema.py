import json

from hal_runtime.cli import EXIT_OK, main
from hal_runtime.evidence_schema import REQUIRED_ARTIFACTS


def test_required_evidence_artifacts_are_fixed():
    assert set(REQUIRED_ARTIFACTS) == {
        "runtime_plan.json", "runtime_report.json",
        "policy_report.json", "policy_decision.json",
    }


def test_list_evidence_schema_cli_and_output(tmp_path):
    assert main(["list-evidence-schema"]) == EXIT_OK
    assert main(["list-evidence-schema", "--out", str(tmp_path)]) == EXIT_OK
    payload = json.loads((tmp_path / "evidence_schema.json").read_text(encoding="utf-8"))
    assert payload["runtime_version"] == payload["evidence_bundle_version"] == "1.0.0"
    assert set(payload["required_artifacts"]) == set(REQUIRED_ARTIFACTS)
    assert payload["simulation_only"] is True
    assert payload["hardware_control_enabled"] is False
