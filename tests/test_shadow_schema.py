from hal_runtime.shadow_schema import shadow_schema_document


def test_shadow_schema_declares_read_only_inputs_and_boundary():
    schema = shadow_schema_document()

    assert schema["runtime_version"] == "1.0.0"
    assert schema["shadow_ingestion_version"] == "1.0.0"
    assert schema["simulation_only"] is True
    assert schema["hardware_control_enabled"] is False
    assert schema["read_only"] is True
    assert schema["claim_boundary"] == "simulation_only_not_certified"
    assert "wafer_map.csv" in schema["supported_files"]
    assert "test_log.jsonl" in schema["supported_files"]
    assert "profile_id" in schema["normalized_fields"]
    assert "confidence" in schema["normalized_fields"]
    assert "not_hardware_control" in schema["known_limitations"]
