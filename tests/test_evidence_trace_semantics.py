import json

from hal_runtime.evidence_bundle_builder import build_evidence_bundle


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_valid_trace_contains_complete_build_lifecycle(tmp_path):
    build_evidence_bundle("samples/evidence_input_valid", tmp_path)
    kinds = {event["event_type"] for event in _events(tmp_path / "evidence_trace.jsonl")}
    assert {
        "evidence_build_started", "artifact_discovered", "artifact_hash_computed",
        "evidence_manifest_built", "evidence_consistency_checked", "evidence_bundle_built",
    } <= kinds


def test_invalid_traces_record_missing_and_safety_events(tmp_path):
    missing = tmp_path / "missing"
    unsafe = tmp_path / "unsafe"
    build_evidence_bundle("samples/evidence_input_missing_required", missing)
    build_evidence_bundle("samples/evidence_input_unsafe_policy", unsafe)
    assert "evidence_required_artifact_missing" in {e["event_type"] for e in _events(missing / "evidence_trace.jsonl")}
    assert "evidence_safety_boundary_violation" in {e["event_type"] for e in _events(unsafe / "evidence_trace.jsonl")}
