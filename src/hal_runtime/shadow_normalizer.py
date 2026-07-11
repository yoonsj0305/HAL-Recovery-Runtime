"""Normalize raw shadow rows into conservative observations."""

from __future__ import annotations

from typing import Any

from .shadow_models import DEFAULT_PROFILE_ID, ShadowObservation, ShadowRawRow
from .shadow_quality import build_observation_quality
from .shadow_schema import (
    ALLOWED_FAILURE_TYPES,
    ALLOWED_OBSERVED_STATUSES,
    ALLOWED_PASS_FAIL,
    ALLOWED_ROLES,
)


def normalize_shadow_rows(
    rows: tuple[ShadowRawRow, ...] | list[ShadowRawRow],
) -> tuple[tuple[ShadowObservation, ...], tuple[str, ...], tuple[dict[str, Any], ...]]:
    observations: list[ShadowObservation] = []
    warnings: list[str] = []
    events: list[dict[str, Any]] = []
    for row in rows:
        observation, row_warnings = normalize_shadow_row(row)
        observations.append(observation)
        warnings.extend(row_warnings)
        events.append(
            {
                "event_type": "shadow_observation_normalized",
                "status": "ok",
                "tile_id": observation.tile_id,
            }
        )
    return tuple(observations), tuple(dict.fromkeys(warnings)), tuple(events)


def normalize_shadow_row(row: ShadowRawRow) -> tuple[ShadowObservation, tuple[str, ...]]:
    values = row.values
    warnings: list[str] = []
    profile_id = _string(values.get("profile_id"))
    if not profile_id:
        profile_id = DEFAULT_PROFILE_ID
        warnings.append("missing_profile_id_defaulted")
    tile_id = _string(values.get("tile_id"))
    if not tile_id:
        warnings.append("missing_tile_id")
    role = _choice(values.get("role"), ALLOWED_ROLES, "unknown")
    if role == "unknown":
        warnings.append("missing_role_defaulted_unknown")
    observed_status = _observed_status(values)
    if observed_status == "unknown":
        warnings.append("missing_observed_status_defaulted_unknown")
    failure_type = _choice(values.get("failure_type"), ALLOWED_FAILURE_TYPES, "unknown")
    pass_fail = _pass_fail(values, observed_status)
    measurement_value = _number(values.get("measurement_value"))
    threshold_min = _number(values.get("threshold_min"))
    threshold_max = _number(values.get("threshold_max"))
    confidence = _confidence(
        observed_status, pass_fail, measurement_value, threshold_min, threshold_max, tile_id
    )
    observation = ShadowObservation(
        profile_id=profile_id,
        die_id=_string(values.get("die_id")),
        wafer_id=_string(values.get("wafer_id")),
        lot_id=_string(values.get("lot_id")),
        tile_id=tile_id,
        x=_number(values.get("x")),
        y=_number(values.get("y")),
        role=role,
        observed_status=observed_status,
        failure_type=failure_type,
        measurement_name=_string(values.get("measurement_name")),
        measurement_value=measurement_value,
        measurement_unit=_string(values.get("measurement_unit")),
        threshold_min=threshold_min,
        threshold_max=threshold_max,
        pass_fail=pass_fail,
        timestamp=_string(values.get("timestamp")),
        source_file=row.source_file,
        source_row=row.source_row,
        confidence=confidence,
    )
    observation = ShadowObservation(
        **{
            **observation.to_dict(),
            "observation_quality": build_observation_quality(observation),
        }
    )
    return (observation, tuple(dict.fromkeys(warnings)))


def _observed_status(values: dict[str, Any]) -> str:
    explicit = _choice(values.get("observed_status"), ALLOWED_OBSERVED_STATUSES, "")
    if explicit:
        return explicit
    status = _choice(values.get("status"), ALLOWED_OBSERVED_STATUSES, "")
    if status:
        return status
    return _pass_fail(values, "unknown")


def _pass_fail(values: dict[str, Any], observed_status: str) -> str:
    explicit = _choice(values.get("pass_fail"), ALLOWED_PASS_FAIL, "")
    if explicit:
        return explicit
    if observed_status in {"pass", "fail"}:
        return observed_status
    return "unknown"


def _confidence(
    observed_status: str,
    pass_fail: str,
    measurement_value: int | float | None,
    threshold_min: int | float | None,
    threshold_max: int | float | None,
    tile_id: str | None,
) -> float:
    if tile_id is None:
        return 0.2
    if (
        (pass_fail in {"pass", "fail"} or observed_status in {"pass", "fail", "degraded"})
        and measurement_value is not None
        and threshold_min is not None
        and threshold_max is not None
    ):
        return 0.8
    if pass_fail in {"pass", "fail"}:
        return 0.6
    if observed_status != "unknown":
        return 0.4
    return 0.2


def _choice(value: Any, allowed: tuple[str, ...], default: str) -> str:
    candidate = _string(value)
    if candidate in allowed:
        return candidate
    return default


def _string(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


def _number(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    if number.is_integer():
        return int(number)
    return number
