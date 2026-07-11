from pathlib import Path

from hal_runtime.evidence_collector import collect_evidence


def test_collector_recognizes_flat_files_and_ignores_unknown_and_nested(tmp_path):
    (tmp_path / "runtime_plan.json").write_text("{}", encoding="utf-8")
    (tmp_path / "unknown.txt").write_text("ignored", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "runtime_report.json").write_text("{}", encoding="utf-8")
    result = collect_evidence(tmp_path)
    assert [artifact.artifact_name for artifact in result.artifacts] == ["runtime_plan.json"]
    assert result.unsupported_artifacts == ("unknown.txt",)
    assert "runtime_report.json" in result.missing_required_artifacts


def test_collector_skips_oversized_artifact(tmp_path):
    path = tmp_path / "runtime_plan.json"
    path.write_text("12345", encoding="utf-8")
    result = collect_evidence(tmp_path, max_size_bytes=4)
    assert result.artifacts == ()
    assert result.warnings == ("artifact_too_large:runtime_plan.json",)
