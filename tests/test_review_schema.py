import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_list_review_gates_exits_zero_and_writes_schema(tmp_path, capsys):
    result = main(["list-review-gates", "--out", str(tmp_path)])

    schema = _read(tmp_path / "review_schema.json")
    gate_ids = {gate["gate_id"] for gate in schema["review_gates"]}
    assert result == EXIT_OK
    assert "candidate_schema_gate" in capsys.readouterr().out
    assert {
        "candidate_schema_gate",
        "candidate_safety_gate",
        "shadow_quality_gate",
        "conflict_review_gate",
        "human_review_decision_gate",
    } <= gate_ids
    assert schema["simulation_only"] is True
    assert schema["hardware_control_enabled"] is False
