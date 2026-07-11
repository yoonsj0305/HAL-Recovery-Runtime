from hal_runtime.shadow_models import DEFAULT_PROFILE_ID, ShadowRawRow
from hal_runtime.shadow_normalizer import normalize_shadow_row, normalize_shadow_rows


def test_shadow_normalizer_defaults_missing_profile_id_and_warns():
    row = ShadowRawRow(
        "test_log.csv",
        1,
        {"tile_id": "TILE_00", "role": "compute_tile", "pass_fail": "pass"},
    )

    observation, warnings = normalize_shadow_row(row)

    assert observation.profile_id == DEFAULT_PROFILE_ID
    assert observation.tile_id == "TILE_00"
    assert observation.observed_status == "pass"
    assert observation.pass_fail == "pass"
    assert observation.confidence == 0.6
    assert warnings == ("missing_profile_id_defaulted",)


def test_shadow_normalizer_measurement_with_thresholds_has_bounded_confidence():
    row = ShadowRawRow(
        "probe_results.jsonl",
        2,
        {
            "profile_id": "P1",
            "tile_id": "TILE_01",
            "role": "memory_tile",
            "pass_fail": "fail",
            "measurement_value": "0.4",
            "threshold_min": "0.8",
            "threshold_max": "1.2",
        },
    )

    observation, warnings = normalize_shadow_row(row)

    assert warnings == ()
    assert observation.measurement_value == 0.4
    assert observation.threshold_min == 0.8
    assert observation.threshold_max == 1.2
    assert observation.confidence == 0.8


def test_shadow_normalizer_emits_trace_events_for_each_row():
    observations, warnings, events = normalize_shadow_rows(
        [
            ShadowRawRow("test_log.csv", 1, {"tile_id": "A", "status": "pass"}),
            ShadowRawRow("test_log.csv", 2, {"tile_id": "B", "status": "unknown"}),
        ]
    )

    assert len(observations) == 2
    assert warnings == (
        "missing_profile_id_defaulted",
        "missing_role_defaulted_unknown",
        "missing_observed_status_defaulted_unknown",
    )
    assert [event["event_type"] for event in events] == [
        "shadow_observation_normalized",
        "shadow_observation_normalized",
    ]


def test_shadow_normalizer_missing_role_and_status_become_unknown():
    row = ShadowRawRow("wafer_map.json", 7, {"profile_id": "P1", "tile_id": "TILE_07"})

    observation, warnings = normalize_shadow_row(row)

    assert warnings == (
        "missing_role_defaulted_unknown",
        "missing_observed_status_defaulted_unknown",
    )
    assert observation.role == "unknown"
    assert observation.observed_status == "unknown"
    assert observation.pass_fail == "unknown"
    assert observation.source_file == "wafer_map.json"
    assert "\\" not in observation.source_file
    assert "/" not in observation.source_file
