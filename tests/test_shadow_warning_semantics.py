import json

from hal_runtime.cli import main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_warnings_are_deterministic_and_sorted(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_low_field_coverage", "--out", str(tmp_path)])

    report = _read(tmp_path / "shadow_ingestion_report.json")

    assert report["warning_reasons"] == sorted(report["warning_reasons"])
    assert "missing_profile_id_defaulted" in report["warning_reasons"]
    assert "missing_role_defaulted_unknown" in report["warning_reasons"]
    assert "low_field_coverage:measurement_fields" in report["warning_reasons"]


def test_missing_profile_warning_string_is_stable(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_missing_profile_id", "--out", str(tmp_path)])

    report = _read(tmp_path / "shadow_ingestion_report.json")

    assert "missing_profile_id_defaulted" in report["warning_reasons"]
