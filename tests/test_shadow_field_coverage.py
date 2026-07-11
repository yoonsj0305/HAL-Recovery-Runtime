import json

from hal_runtime.cli import main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _coverage_values(payload):
    for value in payload.values():
        if isinstance(value, dict):
            yield from _coverage_values(value)
        else:
            yield value


def test_shadow_field_coverage_exists_and_is_fractional(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(tmp_path)])

    observations = _read(tmp_path / "shadow_observations.json")
    coverage = observations["field_coverage"]

    assert "required_like_fields" in coverage
    assert "overall_field_coverage" in coverage
    assert all(0.0 <= value <= 1.0 for value in _coverage_values(coverage))


def test_low_field_coverage_creates_deterministic_warning_and_no_absolute_paths(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_low_field_coverage", "--out", str(tmp_path)])

    report = _read(tmp_path / "shadow_ingestion_report.json")
    observations = _read(tmp_path / "shadow_observations.json")["observations"]

    assert "low_field_coverage:measurement_fields" in report["quality_warning_reasons"]
    for observation in observations:
        assert "\\" not in observation["source_file"]
        assert "/" not in observation["source_file"]
