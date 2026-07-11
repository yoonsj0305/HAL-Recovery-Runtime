import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def test_build_and_validate_evidence_cli(tmp_path):
    bundle = tmp_path / "bundle"
    assert main([
        "build-evidence-bundle", "samples/evidence_input_valid",
        "--out", str(bundle),
    ]) == EXIT_OK
    assert (bundle / "artifacts").is_dir()
    assert {"evidence_manifest.json", "evidence_bundle.json", "evidence_report.json", "evidence_trace.jsonl"} <= {p.name for p in bundle.iterdir()}
    validation = tmp_path / "validation"
    assert main([
        "validate-evidence-bundle", str(bundle), "--out", str(validation),
    ]) == EXIT_OK
    payload = json.loads((validation / "evidence_validation_report.json").read_text(encoding="utf-8"))
    assert payload["hashes_verified"] is True


def test_invalid_evidence_inputs_exit_nonzero(tmp_path):
    for sample in ("evidence_input_missing_required", "evidence_input_unsafe_policy"):
        assert main([
            "build-evidence-bundle", f"samples/{sample}",
            "--out", str(tmp_path / sample),
        ]) == EXIT_INVALID
