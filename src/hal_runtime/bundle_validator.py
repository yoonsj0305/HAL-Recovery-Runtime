"""Cross-artifact consistency checks for Compiler bundles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bundle_loader import CompilerBundle, OPTIONAL_ARTIFACT_NAMES
from .models import RUNTIME_VERSION


@dataclass(frozen=True)
class BundleValidationResult:
    bundle_validation_status: str
    bundle_validation_passed: bool
    bundle_validation_reasons: tuple[str, ...]
    bundle_validation_warnings: tuple[str, ...]
    present_artifacts: tuple[str, ...]
    missing_artifacts: tuple[str, ...]
    profile_id: str | None
    supporting_artifact_count: int
    degraded_bundle_mode: bool
    runtime_version: str = RUNTIME_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_version": self.runtime_version,
            "bundle_validation_status": self.bundle_validation_status,
            "bundle_validation_passed": self.bundle_validation_passed,
            "bundle_validation_reasons": list(self.bundle_validation_reasons),
            "bundle_validation_warnings": list(self.bundle_validation_warnings),
            "present_artifacts": list(self.present_artifacts),
            "missing_artifacts": list(self.missing_artifacts),
            "profile_id": self.profile_id,
            "supporting_artifact_count": self.supporting_artifact_count,
            "degraded_bundle_mode": self.degraded_bundle_mode,
        }


def validate_compiler_bundle(bundle: CompilerBundle) -> BundleValidationResult:
    profile = bundle.recovery_profile
    profile_id = profile.get("profile_id") if profile else None
    if not isinstance(profile_id, str):
        profile_id = None
    supporting_count = sum(
        name in bundle.present_artifacts for name in OPTIONAL_ARTIFACT_NAMES
    )

    if profile is None:
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "invalid_missing_profile",
            ("recovery_profile_missing",),
        )

    optional_load_errors = tuple(
        reason for reason in bundle.load_errors if reason != "recovery_profile_missing"
    )
    if optional_load_errors:
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "invalid_artifact_json",
            optional_load_errors,
        )

    artifacts = (
        ("solver_report.json", bundle.solver_report),
        ("artifact_validation_report.json", bundle.artifact_validation_report),
        ("comparison_report.json", bundle.comparison_report),
        ("functional_passport.json", bundle.functional_passport),
    )
    mismatch_reasons = tuple(
        f"profile_id_mismatch:{name}"
        for name, artifact in artifacts
        if artifact is not None
        and "profile_id" in artifact
        and artifact["profile_id"] != profile_id
    )
    if mismatch_reasons:
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "invalid_profile_id_mismatch",
            mismatch_reasons,
        )

    validation_report = bundle.artifact_validation_report
    if validation_report and (
        validation_report.get("artifact_validation_passed") is False
        or validation_report.get("validation_status") == "failed"
    ):
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "invalid_artifact_validation_failed",
            ("artifact_validation_failed",),
        )

    solver = bundle.solver_report
    if solver and solver.get("solver_status") in {"failed", "infeasible"}:
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "invalid_solver_failed",
            ("solver_failed",),
        )

    comparison = bundle.comparison_report
    if comparison and comparison.get("comparison_status") == "failed":
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "invalid_comparison_failed",
            ("comparison_failed",),
        )

    passport = bundle.functional_passport
    if passport and (
        passport.get("passport_status") == "failed"
        or passport.get("decision_readiness") == "not_ready"
    ):
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "invalid_passport_not_ready",
            ("functional_passport_not_ready",),
        )

    warnings = _comparison_warnings(comparison)
    missing_supporting = tuple(
        name for name in bundle.missing_artifacts if name != "recovery_profile.json"
    )
    if missing_supporting:
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "degraded_missing_artifacts",
            tuple(f"missing_artifact:{name}" for name in missing_supporting),
            warnings,
        )

    if solver and solver.get("solver_status") == "degraded":
        return _result(
            bundle,
            profile_id,
            supporting_count,
            "degraded_solver_status",
            ("solver_degraded",),
            warnings,
        )

    return _result(
        bundle,
        profile_id,
        supporting_count,
        "valid_bundle",
        (),
        warnings,
    )


validate_bundle = validate_compiler_bundle


def _comparison_warnings(comparison: dict[str, Any] | None) -> tuple[str, ...]:
    if not comparison or not isinstance(comparison.get("warnings"), list):
        return ()
    return tuple(str(warning) for warning in comparison["warnings"])


def _result(
    bundle: CompilerBundle,
    profile_id: str | None,
    supporting_count: int,
    status: str,
    reasons: tuple[str, ...],
    warnings: tuple[str, ...] = (),
) -> BundleValidationResult:
    return BundleValidationResult(
        bundle_validation_status=status,
        bundle_validation_passed=not status.startswith("invalid_"),
        bundle_validation_reasons=reasons,
        bundle_validation_warnings=warnings,
        present_artifacts=bundle.present_artifacts,
        missing_artifacts=bundle.missing_artifacts,
        profile_id=profile_id,
        supporting_artifact_count=supporting_count,
        degraded_bundle_mode=status.startswith("degraded_"),
    )
