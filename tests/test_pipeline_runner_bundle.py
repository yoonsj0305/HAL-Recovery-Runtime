import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_run_pipeline_bundle_includes_bundle_gate_and_evidence(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--bundle",
            "samples/compiler_bundle_valid",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    runtime_report = _read(tmp_path / "runtime" / "runtime_report.json")
    assert result == EXIT_OK
    assert report["input_mode"] == "bundle"
    assert runtime_report["bundle_gate_evaluated"] is True
    assert runtime_report["bundle_validation_passed"] is True
    assert runtime_report["bundle_validation_status"] == "valid_bundle"
    assert (tmp_path / "evidence" / "evidence_bundle.json").is_file()
    assert report["evidence_summary"]["evidence_validation_passed"] is True
