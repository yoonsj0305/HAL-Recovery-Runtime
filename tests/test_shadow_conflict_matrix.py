import json

from hal_runtime.cli import main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_conflict_matrix_is_deterministic_and_bounded(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_conflict_multi", "--out", str(tmp_path)])

    observations = _read(tmp_path / "shadow_observations.json")
    matrix = observations["conflict_matrix"]
    tiles = matrix["conflicting_tiles"]

    assert matrix["conflict_count"] > 0
    assert [tile["tile_id"] for tile in tiles] == sorted(tile["tile_id"] for tile in tiles)
    assert all("\\" not in source and "/" not in source for tile in tiles for source in tile["source_files"])
    assert "conflicting_observations:CONFLICT_MULTI_00" in [
        tile["warning"] for tile in tiles
    ]


def test_conflicting_pass_fail_does_not_resolve_to_available(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_conflict_multi", "--out", str(tmp_path)])

    candidate = _read(tmp_path / "recovery_profile_candidate.json")
    tile = next(tile for tile in candidate["tiles"] if tile["tile_id"] == "CONFLICT_MULTI_00")

    assert tile["status"] != "available"
    assert tile["status"] in {"degraded", "unknown"}
    assert "conflicting_observations:CONFLICT_MULTI_00" in candidate["candidate_warnings"]
