import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_list_shadow_schemas_writes_schema(tmp_path, capsys):
    result = main(["list-shadow-schemas", "--out", str(tmp_path)])

    assert result == EXIT_OK
    assert "test_log.csv read_only=true" in capsys.readouterr().out
    assert _read(tmp_path / "shadow_schema.json")["runtime_version"] == "1.0.0"


def test_ingest_shadow_data_writes_all_shadow_artifacts(tmp_path):
    result = main(
        ["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(tmp_path)]
    )

    assert result == EXIT_OK
    assert {path.name for path in tmp_path.iterdir()} == {
        "shadow_schema.json",
        "shadow_observations.json",
        "shadow_ingestion_report.json",
        "recovery_profile_candidate.json",
        "shadow_quality_report.json",
        "shadow_trace.jsonl",
    }
    report = _read(tmp_path / "shadow_ingestion_report.json")
    candidate = _read(tmp_path / "recovery_profile_candidate.json")
    assert report["shadow_ingestion_status"] == "shadow_ingestion_completed"
    assert report["observation_count"] == 4
    assert report["shadow_quality_band"] in {"high", "medium"}
    assert candidate["profile_candidate"] is True
    assert candidate["human_review_required"] is True


def test_ingest_shadow_data_missing_profile_id_is_warning_only(tmp_path):
    result = main(
        [
            "ingest-shadow-data",
            "samples/shadow_input_missing_profile_id",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "shadow_ingestion_report.json")
    observations = _read(tmp_path / "shadow_observations.json")
    assert result == EXIT_OK
    assert report["shadow_ingestion_status"] == "shadow_ingestion_completed_with_warnings"
    assert "missing_profile_id_defaulted" in report["warning_reasons"]
    assert observations["profile_id"] == "SHADOW_PROFILE_001"


def test_ingest_shadow_data_conflict_is_warning_only(tmp_path):
    result = main(
        [
            "ingest-shadow-data",
            "samples/shadow_input_conflict",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "shadow_ingestion_report.json")
    candidate = _read(tmp_path / "recovery_profile_candidate.json")
    assert result == EXIT_OK
    assert report["shadow_ingestion_status"] == "shadow_ingestion_completed_with_warnings"
    assert "conflicting_observations:CONFLICT_TILE_00" in report["warning_reasons"]
    assert candidate["tiles"][0]["status"] == "degraded"


def test_ingest_shadow_data_no_supported_files_is_invalid(tmp_path, capsys):
    result = main(
        [
            "ingest-shadow-data",
            "samples/shadow_input_no_supported_files",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "shadow_ingestion_report.json")
    assert result == EXIT_INVALID
    assert report["shadow_validation_status"] == "invalid_no_supported_files"
    assert "invalid_no_supported_files" in report["blocking_reasons"]
    assert "Shadow ingestion blocked" in capsys.readouterr().err


def test_ingest_shadow_data_invalid_json_is_invalid_when_no_valid_files(tmp_path):
    result = main(
        [
            "ingest-shadow-data",
            "samples/shadow_input_invalid_json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "shadow_ingestion_report.json")
    assert result == EXIT_INVALID
    assert report["shadow_validation_status"] == "invalid_input_format"
    assert "invalid_input_format" in report["blocking_reasons"]
