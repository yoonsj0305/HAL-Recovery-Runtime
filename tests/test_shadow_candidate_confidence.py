import json

from hal_runtime.cli import main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_candidate_confidence_summary_is_safe_and_bounded(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(tmp_path)])

    candidate = _read(tmp_path / "recovery_profile_candidate.json")
    summary = candidate["candidate_confidence_summary"]

    assert summary["candidate_tile_count"] == len(candidate["tiles"])
    assert 0.0 <= summary["average_tile_confidence"] <= 1.0
    assert 0.0 <= summary["min_tile_confidence"] <= summary["max_tile_confidence"] <= 1.0
    assert set(summary["confidence_band_counts"]) == {
        "high",
        "medium",
        "low",
        "insufficient",
    }
    assert summary["safe_for_pipeline_handoff"] is False
    assert summary["requires_human_review"] is True
    assert candidate["assigned_workloads"] == []
