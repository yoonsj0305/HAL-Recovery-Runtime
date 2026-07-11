from hal_runtime.shadow_readers import read_shadow_directory


def test_shadow_reader_loads_csv_and_json_without_recursion():
    result = read_shadow_directory("samples/shadow_input_valid")

    assert len(result.rows) == 4
    assert result.files_supported == ("test_log.csv", "tile_status.json")
    assert result.files_ignored == ()
    assert result.invalid_reasons == ()
    assert result.safety_boundary_violations == ()
    assert {row.source_file for row in result.rows} == {"test_log.csv", "tile_status.json"}


def test_shadow_reader_loads_jsonl_rows():
    result = read_shadow_directory("samples/shadow_input_jsonl")

    assert len(result.rows) == 2
    assert result.files_supported == ("probe_results.jsonl",)
    assert result.rows[0].values["tile_id"] == "JSONL_TILE_00"


def test_shadow_reader_ignores_unsupported_files_as_warnings():
    result = read_shadow_directory("samples/shadow_input_no_supported_files")

    assert result.files_discovered == ("notes.txt",)
    assert result.files_supported == ()
    assert result.files_ignored == ("notes.txt",)
    assert result.warning_reasons == ("unknown_file_ignored:notes.txt",)


def test_shadow_reader_does_not_recurse_directories(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "test_log.csv").write_text(
        "tile_id,observed_status\nNESTED_TILE,pass\n", encoding="utf-8"
    )

    result = read_shadow_directory(tmp_path)

    assert result.files_discovered == ()
    assert result.files_supported == ()
    assert result.rows == ()


def test_shadow_reader_skips_oversized_supported_files(tmp_path):
    oversized = tmp_path / "test_log.csv"
    oversized.write_text("tile_id\n" + ("A\n" * (3 * 1024 * 1024)), encoding="utf-8")

    result = read_shadow_directory(tmp_path)

    assert result.files_supported == ("test_log.csv",)
    assert result.files_skipped == ("test_log.csv",)
    assert result.rows == ()
    assert result.warning_reasons == ("shadow_input_too_large:test_log.csv",)


def test_shadow_reader_records_invalid_json_without_rows():
    result = read_shadow_directory("samples/shadow_input_invalid_json")

    assert result.files_supported == ("test_log.json",)
    assert result.files_skipped == ("test_log.json",)
    assert result.rows == ()
    assert result.invalid_reasons
    assert result.events[-1]["event_type"] == "shadow_input_invalid"


def test_shadow_reader_blocks_unsafe_truthy_fields():
    result = read_shadow_directory("samples/shadow_input_unsafe_field")

    assert result.rows == ()
    assert "hardware_control_enabled_true" in result.safety_boundary_violations
    assert "real_execution_allowed_true" in result.safety_boundary_violations
    assert any(
        event["event_type"] == "shadow_safety_boundary_violation"
        for event in result.events
    )
