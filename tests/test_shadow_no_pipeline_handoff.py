from pathlib import Path

import pytest

from hal_runtime.cli import main
from hal_runtime.shadow_report import ingest_shadow_data


def test_shadow_ingestion_does_not_create_runtime_or_pipeline_artifacts(tmp_path):
    ingest_shadow_data("samples/shadow_input_valid", tmp_path)

    names = {path.name for path in tmp_path.iterdir()}
    assert names == {
        "shadow_schema.json",
        "shadow_observations.json",
        "shadow_ingestion_report.json",
        "recovery_profile_candidate.json",
        "shadow_quality_report.json",
        "shadow_trace.jsonl",
    }
    assert not any(name.startswith("pipeline_") for name in names)
    assert not any(name.startswith("runtime_") for name in names)


def test_shadow_modules_do_not_import_pipeline_runner():
    shadow_sources = Path("src/hal_runtime").glob("shadow_*.py")

    for source in shadow_sources:
        text = source.read_text(encoding="utf-8")
        assert "pipeline_runner" not in text
        assert "run_pipeline" not in text


def test_run_pipeline_does_not_accept_shadow_input_argument():
    with pytest.raises(SystemExit):
        main(["run-pipeline", "--shadow-input", "samples/shadow_input_valid", "--out", "ignored"])
