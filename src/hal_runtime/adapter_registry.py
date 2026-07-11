"""Deterministic registry of built-in mock adapters only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapter_contract import MockAdapter
from .adapter_models import CLAIM_BOUNDARY
from .models import RUNTIME_VERSION
from .mock_adapters import (
    MockMemoryTileAdapter,
    MockRoutingTileAdapter,
    MockSensorTileAdapter,
)


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: tuple[MockAdapter, ...] = (
            MockSensorTileAdapter(),
            MockRoutingTileAdapter(),
            MockMemoryTileAdapter(),
        )

    def list_adapters(self) -> tuple[MockAdapter, ...]:
        return self._adapters

    def resolve(self, action: Mapping[str, Any]) -> tuple[MockAdapter | None, str | None]:
        action_type = action.get("action_type")
        candidates = tuple(
            adapter
            for adapter in self._adapters
            if action_type in adapter.info.supported_action_types
        )
        if not candidates:
            return None, "unsupported_action_type"

        role = _resolve_role(action)
        if role == "__conflict__":
            return None, "role_missing_or_unresolvable"
        if role is None:
            return None, "role_missing_or_unresolvable"
        for adapter in candidates:
            if role in adapter.info.supported_roles:
                return adapter, None
        return None, "role_missing_or_unresolvable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": RUNTIME_VERSION,
            "simulation_only": True,
            "hardware_control_enabled": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "adapters": [adapter.info.to_dict() for adapter in self._adapters],
        }


def _resolve_role(action: Mapping[str, Any]) -> str | None:
    role = action.get("role")
    target_role = action.get("target_role")
    role_value = role if isinstance(role, str) and role else None
    target_value = target_role if isinstance(target_role, str) and target_role else None
    if role_value and target_value and role_value != target_value:
        return "__conflict__"
    return role_value or target_value
