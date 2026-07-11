from hal_runtime.shadow_normalizer import normalize_shadow_rows
from hal_runtime.shadow_profile_builder import build_recovery_profile_candidate
from hal_runtime.shadow_readers import read_shadow_directory


def test_shadow_profile_builder_creates_candidate_only_profile():
    observations, _, _ = normalize_shadow_rows(
        read_shadow_directory("samples/shadow_input_valid").rows
    )

    candidate, warnings = build_recovery_profile_candidate(observations)
    status_by_tile = {tile["tile_id"]: tile["status"] for tile in candidate["tiles"]}

    assert warnings == ()
    assert candidate["runtime_version"] == "1.0.0"
    assert candidate["profile_candidate"] is True
    assert candidate["human_review_required"] is True
    assert candidate["hardware_control_enabled"] is False
    assert candidate["hardware_execution_enabled"] is False
    assert candidate["assigned_workloads"] == []
    assert candidate["preferred_routes"] == []
    assert status_by_tile["TILE_00"] == "available"
    assert status_by_tile["TILE_01"] == "blocked"
    assert status_by_tile["TILE_02"] == "degraded"


def test_shadow_profile_builder_degrades_conflicting_observations():
    observations, _, _ = normalize_shadow_rows(
        read_shadow_directory("samples/shadow_input_conflict").rows
    )

    candidate, warnings = build_recovery_profile_candidate(observations)

    assert warnings == ("conflicting_observations:CONFLICT_TILE_00",)
    assert candidate["tiles"][0]["tile_id"] == "CONFLICT_TILE_00"
    assert candidate["tiles"][0]["status"] == "degraded"
    assert "conflicting_observations:CONFLICT_TILE_00" in candidate["candidate_warnings"]
