import json

from hal_runtime.cli import main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_quality_report_is_written_with_required_semantics(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(tmp_path)])

    report = _read(tmp_path / "shadow_quality_report.json")

    assert report["runtime_version"] == "1.0.0"
    assert report["shadow_quality_semantics_version"] == "1.0.0"
    assert 0.0 <= report["shadow_quality_score"] <= 1.0
    assert report["shadow_quality_band"] in {"high", "medium", "low", "insufficient"}
    assert "field_coverage" in report
    assert "conflict_matrix" in report
    assert "candidate_confidence_summary" in report
    assert "quality_score_is_not_hardware_safety" in report["known_limitations"]
