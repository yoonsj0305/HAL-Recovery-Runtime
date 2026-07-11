"""Internal-function validator for the synthetic public PoC workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .adapter_models import CLAIM_BOUNDARY
from .dry_run_executor import run_dry_run
from .event_log import write_events, write_json
from .models import RUNTIME_VERSION
from .pipeline_runner import run_pipeline
from .profile_loader import load_profile
from .profile_promoter import promote_reviewed_profile
from .release_contract import PUBLIC_POC_CONTRACT_VERSION, release_contract_document
from .review_integrity import sha256_or_none
from .review_package_builder import build_candidate_review
from .review_validator import validate_candidate_review
from .safety_gate import SafetyGate
from .shadow_report import ingest_shadow_data, validate_shadow_data


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXAMPLE_ROOT = PROJECT_ROOT / "examples" / "public_poc"
VALIDATION_KEYS = (
    "release_contract",
    "example_inputs",
    "shadow_ingestion",
    "shadow_quality",
    "candidate_review",
    "review_decision",
    "promotion_lineage",
    "reviewed_profile",
    "runtime_dry_run",
    "safety_invariants",
)


def validate_public_poc(
    output_directory: str | Path,
    example_root: str | Path = DEFAULT_EXAMPLE_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the documented local-file workflow without shell execution."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    workspace = output / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    example = Path(example_root)
    trace: list[dict[str, Any]] = [
        {"event_type": "public_poc_validation_started", "status": "ok"}
    ]
    matrix = {key: _matrix(False, "not_evaluated", []) for key in VALIDATION_KEYS}
    blocking: list[str] = []
    warnings: list[str] = []
    stages: list[dict[str, Any]] = []

    contract = release_contract_document()
    contract_reasons = _release_contract_reasons(contract)
    matrix["release_contract"] = _matrix(not contract_reasons, "ok" if not contract_reasons else "blocked", contract_reasons)
    trace.append(
        {"event_type": "release_contract_validated", "status": "ok" if not contract_reasons else "blocked"}
    )
    blocking.extend(contract_reasons)

    expected, example_reasons = _load_example_expectations(example)
    matrix["example_inputs"] = _matrix(not example_reasons, "ok" if not example_reasons else "blocked", example_reasons)
    blocking.extend(example_reasons)
    if blocking:
        return _finish_invalid(
            output,
            trace,
            matrix,
            stages,
            blocking,
            warnings,
            status="invalid_release_contract" if contract_reasons else "invalid_example_inputs",
        )

    input_dir = example / "input"
    decision_path = example / "review_decision_approved.json"
    shadow_dir = workspace / "shadow"
    shadow_validation_dir = workspace / "shadow_validation"
    review_dir = workspace / "review"
    review_validation_dir = workspace / "review_validation"
    promoted_dir = workspace / "promoted"
    dry_run_dir = workspace / "dry_run"
    pipeline_dir = workspace / "pipeline"

    try:
        _start(trace, "shadow_ingestion")
        shadow_report = ingest_shadow_data(input_dir, shadow_dir)
        shadow_ok = shadow_report["shadow_ingestion_status"] not in {
            "shadow_ingestion_blocked", "shadow_ingestion_failed", "shadow_ingestion_invalid_input"
        }
        _complete(trace, "shadow_ingestion", shadow_ok)
        _stage(stages, "shadow_ingestion", shadow_ok, "shadow")
        matrix["shadow_ingestion"] = _matrix(shadow_ok, "ok" if shadow_ok else "blocked", shadow_report.get("blocking_reasons", []))

        _start(trace, "shadow_validation")
        shadow_validation = validate_shadow_data(shadow_dir, shadow_validation_dir)
        shadow_validation_ok = shadow_validation["shadow_validation_passed"] is True
        _complete(trace, "shadow_validation", shadow_validation_ok)
        _stage(stages, "shadow_validation", shadow_validation_ok, "shadow_validation")
        quality_warnings = sorted(
            dict.fromkeys(
                list(shadow_report.get("quality_warning_reasons", []))
                + list(shadow_validation.get("warning_reasons", []))
            )
        )
        warnings.extend(quality_warnings)
        matrix["shadow_quality"] = _matrix(
            shadow_validation_ok,
            "warnings_present" if quality_warnings else "ok",
            quality_warnings,
        )

        _start(trace, "candidate_review")
        review_report = build_candidate_review(shadow_dir, review_dir)
        review_ok = review_report["candidate_review_passed"] is True
        _complete(trace, "candidate_review", review_ok)
        _stage(stages, "candidate_review", review_ok, "review")
        matrix["candidate_review"] = _matrix(
            review_ok,
            "warnings_present" if review_report.get("candidate_review_warnings") else "ok",
            review_report.get("candidate_review_blocking_reasons", []),
        )

        review_validation = validate_candidate_review(
            review_dir, review_validation_dir, decision_path
        )
        decision_ok = review_validation["promotion_would_be_allowed"] is True
        matrix["review_decision"] = _matrix(
            decision_ok,
            "ok" if decision_ok else "blocked",
            review_validation.get("blocking_reasons", []),
        )
        trace.append(
            {"event_type": "public_poc_review_decision_validated", "status": "ok" if decision_ok else "blocked"}
        )
        _stage(stages, "explicit_review_decision", decision_ok, "review_validation")

        promotion_report = promote_reviewed_profile(review_dir, decision_path, promoted_dir)
        promotion_ok = promotion_report["promotion_passed"] is True
        profile_path = promoted_dir / "reviewed_recovery_profile.json"
        lineage_ok, lineage_reasons = _validate_lineage(
            promotion_report, shadow_dir, review_dir, decision_path
        )
        matrix["promotion_lineage"] = _matrix(
            promotion_ok and lineage_ok,
            "ok" if promotion_ok and lineage_ok else "blocked",
            lineage_reasons + list(promotion_report.get("promotion_blocking_reasons", [])),
        )
        trace.append(
            {"event_type": "public_poc_promotion_lineage_validated", "status": "ok" if promotion_ok and lineage_ok else "blocked"}
        )
        _stage(stages, "dry_run_profile_promotion", promotion_ok and lineage_ok, "promoted")

        profile = load_profile(profile_path)
        gate = SafetyGate().evaluate(profile)
        profile_ok = gate.passed
        matrix["reviewed_profile"] = _matrix(
            profile_ok, "ok" if profile_ok else "blocked", list(gate.failure_reasons)
        )
        _stage(stages, "reviewed_profile_validation", profile_ok, "promoted")

        dry_run = run_dry_run(profile_path, dry_run_dir)
        dry_run_ok = dry_run.report.safety_gate_passed is True
        matrix["runtime_dry_run"] = _matrix(
            dry_run_ok, "ok" if dry_run_ok else "blocked", [] if dry_run_ok else [dry_run.report.runtime_status]
        )
        trace.append(
            {"event_type": "public_poc_dry_run_validated", "status": "ok" if dry_run_ok else "blocked"}
        )
        _stage(stages, "runtime_dry_run", dry_run_ok, "dry_run")

        pipeline = run_pipeline(profile_path=profile_path, output_dir=pipeline_dir)
        pipeline_ok = pipeline.exit_code == 0
        _stage(stages, "optional_simulation_pipeline", pipeline_ok, "pipeline")
        policy = _read_json(pipeline_dir / "policy" / "policy_report.json")
        final_policy = policy.get("selected_policy")
        candidate = _read_json(shadow_dir / "recovery_profile_candidate.json")
        candidate_tiles = candidate.get("tiles", [])
        candidate_tile_count = len(candidate_tiles) if isinstance(candidate_tiles, list) else 0

        expectation_reasons = _expectation_reasons(
            expected,
            profile_id=candidate.get("profile_id"),
            candidate_tile_count=candidate_tile_count,
            final_policy=final_policy,
        )
        safety_reasons = _safety_reasons(
            profile,
            promotion_report,
            expected.get("safety_invariants", {}),
        )
        matrix["safety_invariants"] = _matrix(
            not safety_reasons and not expectation_reasons,
            "ok" if not safety_reasons and not expectation_reasons else "blocked",
            safety_reasons + expectation_reasons,
        )
        trace.append(
            {"event_type": "public_poc_safety_invariants_validated", "status": "ok" if not safety_reasons and not expectation_reasons else "blocked"}
        )

        for name, passed in (
            ("shadow_ingestion", shadow_ok),
            ("shadow_quality", shadow_validation_ok),
            ("candidate_review", review_ok),
            ("review_decision", decision_ok),
            ("promotion_lineage", promotion_ok and lineage_ok),
            ("reviewed_profile", profile_ok),
            ("runtime_dry_run", dry_run_ok),
            ("safety_invariants", not safety_reasons and not expectation_reasons),
        ):
            if not passed:
                blocking.append(f"public_poc_stage_failed:{name}")
        if not pipeline_ok:
            blocking.append("public_poc_stage_failed:optional_simulation_pipeline")

        passed = not blocking
        validation_status = "valid_public_poc" if passed else "invalid_public_poc_artifacts"
        report = _public_poc_report(
            passed=passed,
            stages=stages,
            profile_id=str(candidate.get("profile_id", "unknown")),
            candidate_tile_count=candidate_tile_count,
            dry_run_status=dry_run.report.runtime_status,
            pipeline_status=str(pipeline.summary.get("pipeline_status")),
            final_policy=str(final_policy),
        )
        validation = _validation_report(
            passed=passed,
            status=validation_status,
            matrix=matrix,
            blocking=blocking,
            warnings=warnings,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        blocking.append(f"public_poc_execution_error:{type(exc).__name__}")
        return _finish_invalid(
            output,
            trace,
            matrix,
            stages,
            blocking,
            warnings,
            status="public_poc_execution_failed",
        )

    trace.append(
        {
            "event_type": "public_poc_validation_completed",
            "status": "ok" if validation["validation_passed"] else "blocked",
            "validation_status": validation["validation_status"],
        }
    )
    _write_outputs(output, report, validation, trace)
    return report, validation


def _release_contract_reasons(contract: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if contract.get("runtime_version") != RUNTIME_VERSION:
        reasons.append("release_contract_runtime_version_mismatch")
    if contract.get("public_poc_contract_version") != PUBLIC_POC_CONTRACT_VERSION:
        reasons.append("release_contract_version_mismatch")
    if contract.get("simulation_only") is not True or contract.get("hardware_control_enabled") is not False:
        reasons.append("release_contract_safety_boundary_invalid")
    if contract.get("claim_boundary") != CLAIM_BOUNDARY:
        reasons.append("release_contract_claim_boundary_invalid")
    for command in ("show-release-contract", "validate-public-poc"):
        if command not in contract.get("supported_cli_commands", []):
            reasons.append(f"release_contract_command_missing:{command}")
    manifest_path = PROJECT_ROOT / "PUBLIC_POC_MANIFEST.json"
    try:
        manifest = _read_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return sorted(reasons + ["public_poc_manifest_invalid_or_missing"])
    if manifest.get("version") != RUNTIME_VERSION:
        reasons.append("public_poc_manifest_version_mismatch")
    if manifest.get("simulation_only") is not True or manifest.get("hardware_control_enabled") is not False:
        reasons.append("public_poc_manifest_safety_boundary_invalid")
    return sorted(dict.fromkeys(reasons))


def _load_example_expectations(example: Path) -> tuple[dict[str, Any], list[str]]:
    required = (
        "README.md",
        "input/test_log.csv",
        "input/tile_status.json",
        "review_decision_approved.json",
        "expected/expected_profile_id.txt",
        "expected/expected_candidate_tile_count.txt",
        "expected/expected_final_policy.txt",
        "expected/expected_safety_invariants.json",
    )
    missing = [f"example_file_missing:{name}" for name in required if not (example / name).is_file()]
    if missing:
        return {}, missing
    try:
        expected = {
            "profile_id": (example / "expected" / "expected_profile_id.txt").read_text(encoding="utf-8").strip(),
            "candidate_tile_count": int((example / "expected" / "expected_candidate_tile_count.txt").read_text(encoding="utf-8").strip()),
            "final_policy": (example / "expected" / "expected_final_policy.txt").read_text(encoding="utf-8").strip(),
            "safety_invariants": _read_json(example / "expected" / "expected_safety_invariants.json"),
        }
        decision = _read_json(example / "review_decision_approved.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return {}, ["example_expectations_invalid"]
    reasons: list[str] = []
    if decision.get("human_review_approved") is not True:
        reasons.append("example_review_decision_not_approved")
    if decision.get("approved_for") != "dry_run_only":
        reasons.append("example_review_scope_invalid")
    raw_inputs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (example / "input").iterdir()
        if path.is_file()
    )
    if ":\\" in raw_inputs:
        reasons.append("example_absolute_path_detected")
    return expected, sorted(reasons)


def _validate_lineage(
    promotion_report: dict[str, Any],
    shadow_dir: Path,
    review_dir: Path,
    decision_path: Path,
) -> tuple[bool, list[str]]:
    lineage = promotion_report.get("profile_promotion_lineage", {})
    expected = {
        "candidate_profile_sha256": sha256_or_none(shadow_dir / "recovery_profile_candidate.json"),
        "candidate_review_package_sha256": sha256_or_none(review_dir / "candidate_review_package.json"),
        "candidate_review_report_sha256": sha256_or_none(review_dir / "candidate_review_report.json"),
        "review_decision_sha256": sha256_or_none(decision_path),
    }
    reasons = [
        f"promotion_lineage_hash_mismatch:{name}"
        for name, value in expected.items()
        if not isinstance(lineage, dict) or lineage.get(name) != value
    ]
    if not isinstance(lineage, dict) or lineage.get("promotion_scope") != "dry_run_only":
        reasons.append("promotion_lineage_scope_invalid")
    return not reasons, reasons


def _expectation_reasons(
    expected: dict[str, Any],
    *,
    profile_id: Any,
    candidate_tile_count: int,
    final_policy: Any,
) -> list[str]:
    reasons: list[str] = []
    if profile_id != expected.get("profile_id"):
        reasons.append("expected_profile_id_mismatch")
    if candidate_tile_count != expected.get("candidate_tile_count"):
        reasons.append("expected_candidate_tile_count_mismatch")
    if final_policy != expected.get("final_policy"):
        reasons.append("expected_final_policy_mismatch")
    return reasons


def _safety_reasons(
    profile: dict[str, Any],
    promotion_report: dict[str, Any],
    expected: dict[str, Any],
) -> list[str]:
    actual = {
        "simulation_only": profile.get("simulation_only"),
        "hardware_control_enabled": profile.get("hardware_control_enabled"),
        "hardware_execution_enabled": profile.get("hardware_execution_enabled"),
        "claim_boundary": profile.get("claim_boundary"),
        "approved_for": promotion_report.get("profile_promotion_lineage", {}).get("promotion_scope"),
    }
    return [f"safety_invariant_mismatch:{name}" for name, value in expected.items() if actual.get(name) != value]


def _public_poc_report(
    *,
    passed: bool,
    stages: list[dict[str, Any]],
    profile_id: str,
    candidate_tile_count: int,
    dry_run_status: str,
    pipeline_status: str,
    final_policy: str,
) -> dict[str, Any]:
    return {
        **_boundary(),
        "public_poc_status": "public_poc_completed" if passed else "public_poc_blocked",
        "public_poc_passed": passed,
        "example_data_type": "synthetic",
        "stages": stages,
        "profile_id": profile_id,
        "candidate_tile_count": candidate_tile_count,
        "review_decision_explicit": True,
        "promotion_scope": "dry_run_only",
        "reviewed_profile_valid": passed,
        "dry_run_status": dry_run_status,
        "pipeline_status": pipeline_status,
        "final_selected_policy": final_policy,
        "safety_invariants_passed": passed,
        "known_limitations": [
            "synthetic_example_only",
            "simulation_only",
            "not_certification",
            "not_hardware_control",
            "not_fab_validation",
        ],
    }


def _validation_report(
    *,
    passed: bool,
    status: str,
    matrix: dict[str, Any],
    blocking: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        **_boundary(),
        "validation_passed": passed,
        "validation_status": status,
        "validation_matrix": matrix,
        "blocking_reasons": sorted(dict.fromkeys(blocking)),
        "warning_reasons": sorted(dict.fromkeys(warnings)),
        "known_limitations": [
            "validation_of_synthetic_public_poc_only",
            "not_hardware_validation",
            "not_certification",
        ],
    }


def _finish_invalid(
    output: Path,
    trace: list[dict[str, Any]],
    matrix: dict[str, Any],
    stages: list[dict[str, Any]],
    blocking: list[str],
    warnings: list[str],
    *,
    status: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    report = _public_poc_report(
        passed=False,
        stages=stages,
        profile_id="unknown",
        candidate_tile_count=0,
        dry_run_status="not_run",
        pipeline_status="not_run",
        final_policy="not_selected",
    )
    report["public_poc_status"] = "public_poc_invalid_example" if status == "invalid_example_inputs" else "public_poc_failed"
    validation = _validation_report(
        passed=False,
        status=status,
        matrix=matrix,
        blocking=blocking,
        warnings=warnings,
    )
    trace.append(
        {"event_type": "public_poc_validation_completed", "status": "blocked", "validation_status": status}
    )
    _write_outputs(output, report, validation, trace)
    return report, validation


def _write_outputs(
    output: Path,
    report: dict[str, Any],
    validation: dict[str, Any],
    trace: list[dict[str, Any]],
) -> None:
    write_json(output / "public_poc_report.json", report)
    write_json(output / "public_poc_validation_report.json", validation)
    write_events(output / "public_poc_trace.jsonl", trace)


def _boundary() -> dict[str, Any]:
    return {
        "runtime_version": RUNTIME_VERSION,
        "public_poc_contract_version": PUBLIC_POC_CONTRACT_VERSION,
        "simulation_only": True,
        "hardware_control_enabled": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _matrix(passed: bool, status: str, reasons: list[str]) -> dict[str, Any]:
    return {"passed": passed, "status": status, "reasons": sorted(dict.fromkeys(str(reason) for reason in reasons))}


def _stage(stages: list[dict[str, Any]], name: str, passed: bool, directory: str) -> None:
    stages.append(
        {"stage_name": name, "status": "passed" if passed else "blocked", "artifact_directory": directory, "reasons": [] if passed else [f"stage_failed:{name}"]}
    )


def _start(trace: list[dict[str, Any]], name: str) -> None:
    trace.append({"event_type": "public_poc_stage_started", "status": "ok", "stage_name": name})


def _complete(trace: list[dict[str, Any]], name: str, passed: bool) -> None:
    trace.append({"event_type": "public_poc_stage_completed", "status": "ok" if passed else "blocked", "stage_name": name})


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("json_root_must_be_object")
    return payload
