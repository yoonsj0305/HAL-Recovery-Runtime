"""Command-line interface for HAL Recovery Runtime."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .adapter_registry import AdapterRegistry
from .adapter_simulator import simulate_plan_file
from .bundle_loader import BundleLoadError, load_compiler_bundle
from .bundle_report import build_bundle_validation_report
from .bundle_validator import validate_compiler_bundle
from .compatibility import check_compatibility
from .dry_run_executor import run_bundle_dry_run, run_dry_run, write_plan_artifact
from .event_log import write_json
from .evidence_bundle_builder import build_evidence_bundle
from .evidence_collector import EvidenceCollectionError
from .evidence_schema import (
    ARTIFACT_TYPES,
    REQUIRED_ARTIFACTS,
    evidence_schema_document,
)
from .evidence_trace import write_evidence_trace
from .evidence_validator import validate_built_evidence
from .failure_modes import FAILURE_MODES, failure_modes_document
from .models import RUNTIME_VERSION
from .pipeline_runner import run_pipeline
from .pipeline_stages import pipeline_stages_document
from .policy_rules import POLICY_MODES, policy_modes_document
from .policy_simulator import simulate_policy_file
from .profile_loader import ProfileLoadError, load_profile
from .profile_promoter import promote_reviewed_profile
from .public_poc_validator import DEFAULT_EXAMPLE_ROOT, validate_public_poc
from .release_contract import release_contract_document
from .review_package_builder import build_candidate_review
from .review_schema import review_schema_document
from .review_validator import validate_candidate_review
from .safety_gate import SafetyGate
from .rollback_simulator import simulate_failure_file
from .shadow_report import ingest_shadow_data, validate_shadow_data
from .shadow_schema import SUPPORTED_SHADOW_FILES, shadow_schema_document


EXIT_OK = 0
EXIT_INVALID = 2
EXIT_ACTIONS_BLOCKED = 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hal-rr", description="Simulation-only HAL recovery profile runtime."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-profile", help="Validate a compiler profile.")
    validate.add_argument("profile")

    check_compat = subparsers.add_parser(
        "check-compat", help="Check profile compatibility without creating artifacts."
    )
    check_compat.add_argument("profile")

    plan = subparsers.add_parser("plan", help="Write an inert runtime plan.")
    plan.add_argument("profile")
    plan.add_argument("--out", required=True)

    dry_run = subparsers.add_parser("dry-run", help="Simulate and write all runtime artifacts.")
    dry_run.add_argument("profile")
    dry_run.add_argument("--out", required=True)

    validate_bundle = subparsers.add_parser(
        "validate-bundle", help="Validate a Compiler artifact bundle."
    )
    validate_bundle.add_argument("bundle")
    validate_bundle.add_argument("--out")

    dry_run_bundle = subparsers.add_parser(
        "dry-run-bundle", help="Simulate from a validated Compiler artifact bundle."
    )
    dry_run_bundle.add_argument("bundle")
    dry_run_bundle.add_argument("--out", required=True)

    list_adapters = subparsers.add_parser(
        "list-adapters", help="List built-in simulation-only mock adapters."
    )
    list_adapters.add_argument("--out")

    simulate_plan = subparsers.add_parser(
        "simulate-plan", help="Simulate an inert Runtime plan through mock adapters."
    )
    simulate_plan.add_argument("plan")
    simulate_plan.add_argument("--out", required=True)

    list_failure_modes = subparsers.add_parser(
        "list-failure-modes", help="List built-in simulation-only failure modes."
    )
    list_failure_modes.add_argument("--out")

    simulate_failure = subparsers.add_parser(
        "simulate-failure", help="Inject a simulated failure and plan inert rollback markers."
    )
    simulate_failure.add_argument("plan")
    simulate_failure.add_argument("--scenario")
    simulate_failure.add_argument("--out", required=True)

    list_policies = subparsers.add_parser(
        "list-policies", help="List built-in simulation-only policy modes."
    )
    list_policies.add_argument("--out")

    simulate_policy = subparsers.add_parser(
        "simulate-policy", help="Select a simulated policy from Runtime artifacts."
    )
    simulate_policy.add_argument("plan")
    simulate_policy.add_argument("--adapter-report")
    simulate_policy.add_argument("--rollback-report")
    simulate_policy.add_argument("--policy-config")
    simulate_policy.add_argument("--out", required=True)

    list_evidence = subparsers.add_parser(
        "list-evidence-schema", help="List recognized evidence artifacts."
    )
    list_evidence.add_argument("--out")

    build_evidence = subparsers.add_parser(
        "build-evidence-bundle", help="Build a simulation-only evidence bundle."
    )
    build_evidence.add_argument("source")
    build_evidence.add_argument("--out", required=True)

    validate_evidence = subparsers.add_parser(
        "validate-evidence-bundle", help="Validate a built evidence bundle."
    )
    validate_evidence.add_argument("bundle")
    validate_evidence.add_argument("--out", required=True)

    list_pipeline_stages = subparsers.add_parser(
        "list-pipeline-stages", help="List fixed simulation-only pipeline stages."
    )
    list_pipeline_stages.add_argument("--out")

    run_pipeline_parser = subparsers.add_parser(
        "run-pipeline", help="Run the simulation-only end-to-end pipeline."
    )
    run_pipeline_parser.add_argument("--profile")
    run_pipeline_parser.add_argument("--bundle")
    run_pipeline_parser.add_argument("--failure-scenario")
    run_pipeline_parser.add_argument("--policy-config")
    run_pipeline_parser.add_argument("--stop-on-warning", action="store_true")
    run_pipeline_parser.add_argument("--no-evidence", action="store_true")
    run_pipeline_parser.add_argument("--out", required=True)

    list_shadow = subparsers.add_parser(
        "list-shadow-schemas", help="List read-only shadow ingestion schemas."
    )
    list_shadow.add_argument("--out")

    ingest_shadow = subparsers.add_parser(
        "ingest-shadow-data", help="Ingest local chip/test data files read-only."
    )
    ingest_shadow.add_argument("source")
    ingest_shadow.add_argument("--out", required=True)

    validate_shadow = subparsers.add_parser(
        "validate-shadow-data", help="Validate built shadow ingestion artifacts."
    )
    validate_shadow.add_argument("source")
    validate_shadow.add_argument("--out", required=True)

    list_review = subparsers.add_parser(
        "list-review-gates", help="List candidate review gates."
    )
    list_review.add_argument("--out")

    build_review = subparsers.add_parser(
        "build-candidate-review", help="Build a simulation-only candidate review package."
    )
    build_review.add_argument("source")
    build_review.add_argument("--out", required=True)

    validate_review = subparsers.add_parser(
        "validate-candidate-review", help="Validate a candidate review package."
    )
    validate_review.add_argument("source")
    validate_review.add_argument("--review-decision")
    validate_review.add_argument("--out", required=True)

    promote_review = subparsers.add_parser(
        "promote-reviewed-profile",
        help="Promote a reviewed candidate to a dry-run-only reviewed profile.",
    )
    promote_review.add_argument("source")
    promote_review.add_argument("--review-decision", required=True)
    promote_review.add_argument("--out", required=True)

    show_contract = subparsers.add_parser(
        "show-release-contract",
        help="Show the stable simulation-only public PoC contract.",
    )
    show_contract.add_argument("--out")

    validate_poc = subparsers.add_parser(
        "validate-public-poc",
        help="Validate the synthetic local-file public PoC without hardware access.",
    )
    validate_poc.add_argument("--example-root", default=str(DEFAULT_EXAMPLE_ROOT))
    validate_poc.add_argument("--out", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "show-release-contract":
            document = release_contract_document()
            print(
                "HAL Recovery Runtime public PoC contract "
                f"v{document['public_poc_contract_version']} "
                "simulation_only=true hardware_control_enabled=false"
            )
            if args.out:
                write_json(Path(args.out) / "release_contract.json", document)
            return EXIT_OK

        if args.command == "validate-public-poc":
            _report, validation = validate_public_poc(args.out, args.example_root)
            status = validation["validation_status"]
            if not validation["validation_passed"]:
                print(f"Public PoC validation failed: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Public PoC validation completed: {status}")
            return EXIT_OK

        if args.command == "list-shadow-schemas":
            for name in SUPPORTED_SHADOW_FILES:
                print(f"{name} read_only=true")
            if args.out:
                write_json(Path(args.out) / "shadow_schema.json", shadow_schema_document())
            return EXIT_OK

        if args.command == "ingest-shadow-data":
            report = ingest_shadow_data(args.source, args.out)
            status = report["shadow_ingestion_status"]
            if status in {
                "shadow_ingestion_blocked",
                "shadow_ingestion_failed",
                "shadow_ingestion_invalid_input",
            }:
                print(f"Shadow ingestion blocked: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Shadow ingestion completed: {status}")
            return EXIT_OK

        if args.command == "validate-shadow-data":
            report = validate_shadow_data(args.source, args.out)
            status = report["shadow_validation_status"]
            if not report["shadow_validation_passed"]:
                print(f"Shadow validation failed: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Shadow validation completed: {status}")
            return EXIT_OK

        if args.command == "list-review-gates":
            document = review_schema_document()
            for gate in document["review_gates"]:
                print(f"{gate['gate_id']} required={gate['required']}")
            if args.out:
                write_json(Path(args.out) / "review_schema.json", document)
            return EXIT_OK

        if args.command == "build-candidate-review":
            report = build_candidate_review(args.source, args.out)
            status = report["candidate_review_status"]
            if not report["candidate_review_passed"]:
                print(f"Candidate review blocked: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Candidate review built: {status}")
            return EXIT_OK

        if args.command == "validate-candidate-review":
            report = validate_candidate_review(
                args.source, args.out, args.review_decision
            )
            status = report["candidate_review_validation_status"]
            if not report["candidate_review_validation_passed"]:
                print(f"Candidate review validation failed: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Candidate review validation completed: {status}")
            return EXIT_OK

        if args.command == "promote-reviewed-profile":
            report = promote_reviewed_profile(
                args.source, args.review_decision, args.out
            )
            status = report["promotion_status"]
            if not report["promotion_passed"]:
                print(f"Profile promotion blocked: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Reviewed profile promoted: {status}")
            return EXIT_OK

        if args.command == "list-pipeline-stages":
            document = pipeline_stages_document()
            for stage in document["stages"]:
                print(f"{stage['stage_id']} {stage['stage_name']} required={stage['required']}")
            if args.out:
                write_json(Path(args.out) / "pipeline_stages.json", document)
            return EXIT_OK

        if args.command == "run-pipeline":
            result = run_pipeline(
                profile_path=args.profile,
                bundle_path=args.bundle,
                output_dir=args.out,
                failure_scenario_path=args.failure_scenario,
                policy_config_path=args.policy_config,
                stop_on_warning=args.stop_on_warning,
                no_evidence=args.no_evidence,
            )
            status = result.summary["pipeline_status"]
            if result.exit_code != EXIT_OK:
                print(f"Pipeline blocked: {status}", file=sys.stderr)
                return result.exit_code
            print(f"Pipeline completed: {status}")
            return EXIT_OK

        if args.command == "list-evidence-schema":
            for name, artifact_type in ARTIFACT_TYPES.items():
                required = "required" if name in REQUIRED_ARTIFACTS else "optional"
                print(f"{name} type={artifact_type} requirement={required}")
            if args.out:
                write_json(
                    Path(args.out) / "evidence_schema.json",
                    evidence_schema_document(),
                )
            return EXIT_OK

        if args.command == "build-evidence-bundle":
            outcome = build_evidence_bundle(args.source, args.out)
            status = outcome.report["evidence_validation_status"]
            if not outcome.report["evidence_validation_passed"]:
                print(f"Evidence bundle invalid: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Evidence bundle built: {status}")
            return EXIT_OK

        if args.command == "validate-evidence-bundle":
            outcome = validate_built_evidence(args.bundle)
            write_json(
                Path(args.out) / "evidence_validation_report.json",
                outcome.report,
            )
            write_evidence_trace(
                Path(args.out) / "evidence_trace.jsonl", outcome.trace_events
            )
            status = outcome.report["evidence_validation_status"]
            if not outcome.report["evidence_validation_passed"]:
                print(f"Evidence validation failed: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Evidence validation completed: {status}")
            return EXIT_OK

        if args.command == "list-policies":
            for mode in POLICY_MODES:
                print(f"{mode.policy_mode} description={mode.description}")
            if args.out:
                write_json(Path(args.out) / "policy_modes.json", policy_modes_document())
            return EXIT_OK

        if args.command == "simulate-policy":
            outcome = simulate_policy_file(
                args.plan,
                args.out,
                args.adapter_report,
                args.rollback_report,
                args.policy_config,
            )
            status = outcome.decision.policy_status
            if status in {
                "invalid_policy_input",
                "blocked_by_safety_boundary",
                "blocked_invalid_artifacts",
                "blocked_policy_config_safety_boundary",
            }:
                print(f"Policy simulation blocked: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Policy simulation completed: {status}")
            return EXIT_OK

        if args.command == "list-failure-modes":
            for mode in FAILURE_MODES:
                print(
                    f"{mode.failure_mode} strategy={mode.rollback_strategy} "
                    f"description={mode.description}"
                )
            if args.out:
                write_json(Path(args.out) / "failure_modes.json", failure_modes_document())
            return EXIT_OK

        if args.command == "simulate-failure":
            outcome = simulate_failure_file(args.plan, args.out, args.scenario)
            status = outcome.rollback_report.rollback_simulation_status
            if status in {
                "invalid_plan",
                "blocked_scenario_safety_boundary",
                "blocked_plan_safety_boundary",
            }:
                print(f"Failure simulation blocked: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Failure simulation completed: {status}")
            return EXIT_OK

        if args.command == "list-adapters":
            registry = AdapterRegistry()
            for adapter in registry.list_adapters():
                info = adapter.info
                print(
                    f"{info.adapter_id} type={info.adapter_type} "
                    f"actions={','.join(info.supported_action_types)} "
                    f"roles={','.join(info.supported_roles)}"
                )
            if args.out:
                write_json(Path(args.out) / "adapter_registry.json", registry.to_dict())
            return EXIT_OK

        if args.command == "simulate-plan":
            outcome = simulate_plan_file(args.plan, args.out)
            status = outcome.report.adapter_simulation_status
            if status in {"invalid_plan", "blocked_safety_boundary"}:
                print(f"Adapter simulation blocked: {status}", file=sys.stderr)
                return EXIT_INVALID
            print(f"Adapter simulation completed: {status}")
            return EXIT_OK

        if args.command == "check-compat":
            result = check_compatibility(load_profile(args.profile))
            if not result.compatible:
                details = [f"missing {field}" for field in result.missing_fields]
                details.extend(result.warnings)
                print(
                    f"Profile incompatible with HAL Recovery Runtime v{RUNTIME_VERSION}: "
                    + ", ".join(details),
                    file=sys.stderr,
                )
                return EXIT_INVALID
            print(f"Profile compatible with HAL Recovery Runtime v{RUNTIME_VERSION}.")
            if result.warnings:
                print("Compatibility warnings: " + ", ".join(result.warnings))
            return EXIT_OK

        if args.command == "validate-bundle":
            bundle = load_compiler_bundle(args.bundle)
            validation = validate_compiler_bundle(bundle)
            profile = bundle.recovery_profile
            compatibility_passed = False
            safety_passed = False
            safety_reasons: tuple[str, ...] = ()
            if profile is not None:
                compatibility_passed = check_compatibility(profile).compatible
                safety_result = SafetyGate().evaluate(profile)
                safety_passed = safety_result.passed
                safety_reasons = safety_result.failure_reasons
            if profile is None:
                validation_stage = "bundle_load"
            elif not compatibility_passed:
                validation_stage = "compatibility_check"
            elif not validation.bundle_validation_passed:
                validation_stage = "bundle_validation"
            elif not safety_passed:
                validation_stage = "safety_gate"
            else:
                validation_stage = "validated"
            if args.out:
                write_json(
                    Path(args.out) / "bundle_validation_report.json",
                    build_bundle_validation_report(validation, validation_stage),
                )
            if not validation.bundle_validation_passed:
                print(
                    f"Bundle blocked: {validation.bundle_validation_status}",
                    file=sys.stderr,
                )
                return EXIT_INVALID
            if not compatibility_passed:
                print("Bundle profile incompatible with Runtime.", file=sys.stderr)
                return EXIT_INVALID
            if not safety_passed:
                print(
                    "Bundle profile blocked: " + ", ".join(safety_reasons),
                    file=sys.stderr,
                )
                return EXIT_INVALID
            print(f"Bundle validated: {validation.bundle_validation_status}.")
            return EXIT_OK

        if args.command == "dry-run-bundle":
            result = run_bundle_dry_run(args.bundle, args.out)
            if (
                not result.report.bundle_validation_passed
                or not result.report.safety_gate_passed
            ):
                print(
                    f"Bundle dry-run blocked ({result.report.runtime_status}); artifacts written: {args.out}",
                    file=sys.stderr,
                )
                return EXIT_INVALID
            print(f"Bundle dry-run completed ({result.report.runtime_status}): {args.out}")
            return EXIT_OK

        if args.command == "validate-profile":
            gate_result = SafetyGate().evaluate(load_profile(args.profile))
            if not gate_result.passed:
                print(
                    "Profile blocked: " + ", ".join(gate_result.failure_reasons),
                    file=sys.stderr,
                )
                return EXIT_INVALID
            if gate_result.degraded_mode:
                print("Profile valid: degraded mode required (preferred_routes missing).")
            else:
                print("Profile valid: safety gate passed.")
            return EXIT_OK

        if args.command == "plan":
            plan, gate_result = write_plan_artifact(args.profile, args.out)
            if not gate_result.passed:
                print(
                    "Plan blocked: " + ", ".join(gate_result.failure_reasons),
                    file=sys.stderr,
                )
                return EXIT_INVALID
            if plan.blocked_actions:
                print(f"Plan written with {len(plan.blocked_actions)} blocked action(s): {args.out}")
                return EXIT_ACTIONS_BLOCKED
            if gate_result.degraded_mode:
                print(f"Degraded plan written with no actions: {args.out}")
            else:
                print(f"Plan written: {args.out}")
            return EXIT_OK

        result = run_dry_run(args.profile, args.out)
        if not result.report.safety_gate_passed:
            print(
                f"Dry-run blocked by safety gate; artifacts written: {args.out}",
                file=sys.stderr,
            )
            return EXIT_INVALID
        print(f"Dry-run completed ({result.report.runtime_status}): {args.out}")
        return EXIT_OK
    except (ProfileLoadError, BundleLoadError, EvidenceCollectionError) as exc:
        print(f"Profile error: {exc}", file=sys.stderr)
        return EXIT_INVALID
    except OSError as exc:
        print(f"Output error: {exc}", file=sys.stderr)
        return EXIT_INVALID


if __name__ == "__main__":
    raise SystemExit(main())
