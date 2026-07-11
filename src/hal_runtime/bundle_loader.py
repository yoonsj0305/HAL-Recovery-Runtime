"""Load HAL Recovery Compiler artifact bundles without mutation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ARTIFACT_NAMES = (
    "recovery_profile.json",
    "solver_report.json",
    "artifact_validation_report.json",
    "comparison_report.json",
    "functional_passport.json",
)
OPTIONAL_ARTIFACT_NAMES = ARTIFACT_NAMES[1:]


class BundleLoadError(ValueError):
    """Raised when the required recovery profile cannot be decoded."""


@dataclass(frozen=True)
class CompilerBundle:
    bundle_path: str
    recovery_profile: dict[str, Any] | None
    solver_report: dict[str, Any] | None
    artifact_validation_report: dict[str, Any] | None
    comparison_report: dict[str, Any] | None
    functional_passport: dict[str, Any] | None
    present_artifacts: tuple[str, ...]
    missing_artifacts: tuple[str, ...]
    load_errors: tuple[str, ...]


def _read_json_object(path: Path, reason: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleLoadError(reason) from exc
    if not isinstance(payload, dict):
        raise BundleLoadError(reason)
    return payload


def load_compiler_bundle(bundle_path: str | Path) -> CompilerBundle:
    path = Path(bundle_path)
    present = tuple(name for name in ARTIFACT_NAMES if (path / name).is_file())
    missing = tuple(name for name in ARTIFACT_NAMES if name not in present)
    load_errors: list[str] = []

    profile: dict[str, Any] | None = None
    if "recovery_profile.json" not in present:
        load_errors.append("recovery_profile_missing")
    else:
        profile = _read_json_object(
            path / "recovery_profile.json", "recovery_profile_invalid_json"
        )

    loaded_optional: dict[str, dict[str, Any] | None] = {}
    for name in OPTIONAL_ARTIFACT_NAMES:
        field = name.removesuffix(".json")
        if name not in present:
            loaded_optional[field] = None
            continue
        reason = f"{field}_invalid_json"
        try:
            loaded_optional[field] = _read_json_object(path / name, reason)
        except BundleLoadError:
            loaded_optional[field] = None
            load_errors.append(reason)

    return CompilerBundle(
        bundle_path=str(path),
        recovery_profile=profile,
        solver_report=loaded_optional["solver_report"],
        artifact_validation_report=loaded_optional["artifact_validation_report"],
        comparison_report=loaded_optional["comparison_report"],
        functional_passport=loaded_optional["functional_passport"],
        present_artifacts=present,
        missing_artifacts=missing,
        load_errors=tuple(load_errors),
    )


load_bundle = load_compiler_bundle
