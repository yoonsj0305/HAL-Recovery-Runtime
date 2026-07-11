"""Built-in adapters that produce records only and have no external I/O."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .adapter_models import MockAdapterInfo, MockAdapterResult


class _RoleMockAdapter:
    adapter_id: str
    adapter_type: str

    @property
    def info(self) -> MockAdapterInfo:
        return MockAdapterInfo(
            adapter_id=self.adapter_id,
            adapter_type=self.adapter_type,
            supported_action_types=("assign_workload",),
            supported_roles=(self.adapter_type,),
        )

    def simulate(self, action: Mapping[str, Any]) -> MockAdapterResult:
        action_id = str(action.get("action_id", "unknown"))
        action_type = str(action.get("action_type", "unknown"))
        workload_id = action.get("workload_id")
        workload = workload_id if isinstance(workload_id, str) else None
        if action_type not in self.info.supported_action_types:
            return MockAdapterResult(
                self.adapter_id,
                action_id,
                action_type,
                workload,
                "blocked_unsupported_action",
                "action_type_not_supported_by_mock_adapter",
            )
        role = _action_role(action)
        if role is not None and role not in self.info.supported_roles:
            return MockAdapterResult(
                self.adapter_id,
                action_id,
                action_type,
                workload,
                "blocked_unsupported_role",
                "role_not_supported_by_mock_adapter",
            )
        return MockAdapterResult(
            self.adapter_id,
            action_id,
            action_type,
            workload,
            "simulated",
            "mock_adapter_contract_accepted",
        )


class MockSensorTileAdapter(_RoleMockAdapter):
    adapter_id = "mock_sensor_tile_adapter"
    adapter_type = "sensor_tile"


class MockRoutingTileAdapter(_RoleMockAdapter):
    adapter_id = "mock_routing_tile_adapter"
    adapter_type = "routing_tile"


class MockMemoryTileAdapter(_RoleMockAdapter):
    adapter_id = "mock_memory_tile_adapter"
    adapter_type = "memory_tile"


def _action_role(action: Mapping[str, Any]) -> str | None:
    role = action.get("role")
    target_role = action.get("target_role")
    if isinstance(role, str):
        return role
    if isinstance(target_role, str):
        return target_role
    return None

