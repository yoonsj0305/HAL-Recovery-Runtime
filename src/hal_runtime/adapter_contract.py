"""Pure software contract implemented by built-in mock adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .adapter_models import MockAdapterInfo, MockAdapterResult


class MockAdapter(Protocol):
    @property
    def info(self) -> MockAdapterInfo: ...

    def simulate(self, action: Mapping[str, Any]) -> MockAdapterResult: ...

