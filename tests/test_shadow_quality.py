import json

from hal_runtime.cli import main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_shadow_observations_include_quality_for_every_observation(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_quality_mixed", "--out", str(tmp_path)])

    observations = _read(tmp_path / "shadow_observations.json")["observations"]

    assert observations
    assert all("observation_quality" in observation for observation in observations)
    assert all(
        0.0 <= observation["observation_quality"]["quality_score"] <= 1.0
        for observation in observations
    )
    assert all(
        observation["observation_quality"]["quality_band"]
        in {"high", "medium", "low", "insufficient"}
        for observation in observations
    )
    assert not any(
        "hardware_safety" in observation["observation_quality"]
        for observation in observations
    )


def test_shadow_quality_bands_follow_conservative_rules(tmp_path):
    main(["ingest-shadow-data", "samples/shadow_input_quality_mixed", "--out", str(tmp_path)])
    observations = {
        observation["tile_id"]: observation
        for observation in _read(tmp_path / "shadow_observations.json")["observations"]
    }
    missing_tile = next(
        observation
        for observation in _read(tmp_path / "shadow_observations.json")["observations"]
        if observation["tile_id"] is None
    )

    assert observations["MIXED_TILE_HIGH"]["observation_quality"]["quality_band"] == "high"
    assert observations["MIXED_TILE_MEDIUM"]["observation_quality"]["quality_band"] == "medium"
    assert observations["MIXED_TILE_LOW"]["observation_quality"]["quality_band"] in {
        "low",
        "medium",
    }
    assert missing_tile["observation_quality"]["quality_band"] == "insufficient"
