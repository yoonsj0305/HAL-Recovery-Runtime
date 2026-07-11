"""Standalone bundle-validation report construction."""

from __future__ import annotations

from typing import Any

from .bundle_validator import BundleValidationResult


def build_bundle_validation_report(
    result: BundleValidationResult,
    validation_stage: str = "validated",
) -> dict[str, Any]:
    report = result.to_dict()
    report["bundle_mode"] = True
    report["validation_stage"] = validation_stage
    return report
