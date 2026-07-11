import json

from hal_runtime.cli import EXIT_OK, main


def test_list_pipeline_stages_exits_zero(capsys):
    result = main(["list-pipeline-stages"])

    assert result == EXIT_OK
    assert "input_load" in capsys.readouterr().out


def test_list_pipeline_stages_writes_document(tmp_path):
    result = main(["list-pipeline-stages", "--out", str(tmp_path)])

    payload = json.loads((tmp_path / "pipeline_stages.json").read_text(encoding="utf-8"))
    stage_names = {stage["stage_name"] for stage in payload["stages"]}
    assert result == EXIT_OK
    assert payload["runtime_version"] == "1.0.0"
    assert payload["pipeline_runner_version"] == "1.0.0"
    assert payload["simulation_only"] is True
    assert payload["hardware_control_enabled"] is False
    assert {
        "input_load",
        "runtime_dry_run",
        "adapter_simulation",
        "failure_rollback_simulation",
        "policy_simulation",
        "evidence_bundle",
        "pipeline_report",
    } <= stage_names
