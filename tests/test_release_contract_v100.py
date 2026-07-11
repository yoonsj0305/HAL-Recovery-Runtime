import json

from hal_runtime.cli import EXIT_OK, main
from hal_runtime.release_contract import SUPPORTED_CLI_COMMANDS, release_contract_document


def test_release_contract_is_deterministic_and_path_free():
    first = release_contract_document()
    second = release_contract_document()
    assert first == second
    assert first["runtime_version"] == first["public_poc_contract_version"] == "1.0.0"
    assert first["simulation_only"] is True
    assert first["hardware_control_enabled"] is False
    assert first["claim_boundary"] == "simulation_only_not_certified"
    assert tuple(first["supported_cli_commands"]) == SUPPORTED_CLI_COMMANDS
    assert {"show-release-contract", "validate-public-poc"} <= set(first["supported_cli_commands"])
    assert ":\\" not in json.dumps(first)


def test_show_release_contract_writes_contract(tmp_path):
    assert main(["show-release-contract", "--out", str(tmp_path)]) == EXIT_OK
    payload = json.loads((tmp_path / "release_contract.json").read_text(encoding="utf-8"))
    assert payload == release_contract_document()

