"""Build candidate-only recovery profiles from shadow observations."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .shadow_models import ShadowObservation, shadow_boundary_fields
from .shadow_quality import (
    build_candidate_confidence_summary,
    build_conflict_matrix,
    conflict_warnings,
)
from .shadow_schema import ALLOWED_CANDIDATE_ROLES


def build_recovery_profile_candidate(
    observations: tuple[ShadowObservation, ...] | list[ShadowObservation],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    profile_id = observations[0].profile_id if observations else "SHADOW_PROFILE_001"
    warnings: list[str] = []
    conflict_matrix = build_conflict_matrix(observations)
    warnings.extend(conflict_warnings(conflict_matrix))
    conflict_tiles = {
        str(item["tile_id"])
        for item in conflict_matrix.get("conflicting_tiles", [])
        if isinstance(item, dict) and item.get("tile_id")
    }
    by_tile: dict[str, list[ShadowObservation]] = defaultdict(list)
    for observation in observations:
        if observation.tile_id:
            by_tile[observation.tile_id].append(observation)
    tiles: list[dict[str, Any]] = []
    for tile_id in sorted(by_tile):
        tile_observations = by_tile[tile_id]
        statuses = {observation.observed_status for observation in tile_observations}
        role = _most_common(
            observation.role for observation in tile_observations if observation.role != "unknown"
        ) or "unknown"
        tile_status = _tile_status(statuses, tile_id in conflict_tiles)
        confidence = min(observation.confidence for observation in tile_observations)
        tiles.append(
            {
                "tile_id": tile_id,
                "role": role,
                "status": tile_status,
                "confidence": confidence,
                "evidence_count": len(tile_observations),
            }
        )
    candidate = {
            **shadow_boundary_fields(),
            "profile_id": profile_id,
            "profile_candidate": True,
            "human_review_required": True,
            "hardware_execution_enabled": False,
            "runtime_loader_hint": "simulation_only",
            "voltage_policy": "no_hardware_control",
            "tiles": tiles,
            "assigned_workloads": [],
            "unassigned_workloads": [],
            "preferred_routes": [],
            "blocked_roles": [],
            "allowed_roles": list(ALLOWED_CANDIDATE_ROLES),
            "candidate_reasons": [
                "profile_candidate_built_from_shadow_observations"
            ],
            "candidate_warnings": list(dict.fromkeys(warnings)),
            "known_limitations": [
                "candidate_only",
                "requires_human_review",
                "not_certified",
                "no_hardware_control",
                "not_safe_for_direct_hardware_application",
            ],
        }
    candidate["candidate_confidence_summary"] = build_candidate_confidence_summary(
        candidate, tuple(dict.fromkeys(warnings))
    )
    return (candidate, tuple(dict.fromkeys(warnings)))


def _tile_status(statuses: set[str], has_conflict: bool) -> str:
    if has_conflict or "degraded" in statuses or ("pass" in statuses and "fail" in statuses):
        return "degraded"
    if "fail" in statuses:
        return "blocked"
    if "pass" in statuses:
        return "available"
    return "unknown"


def _most_common(values) -> str | None:
    items = [value for value in values if value]
    if not items:
        return None
    return Counter(items).most_common(1)[0][0]
