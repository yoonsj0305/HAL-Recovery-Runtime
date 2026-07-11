"""Read compiler profiles without modifying them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ProfileLoadError(ValueError):
    """Raised when a profile cannot be loaded as a JSON object."""


def load_profile(path: str | Path) -> dict[str, Any]:
    profile_path = Path(path)
    try:
        raw = profile_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProfileLoadError(f"profile_not_readable: {profile_path}") from exc

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProfileLoadError(
            f"profile_invalid_json: line={exc.lineno} column={exc.colno}"
        ) from exc

    if not isinstance(profile, dict):
        raise ProfileLoadError("profile_root_must_be_object")
    return profile

