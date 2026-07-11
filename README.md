# HAL Recovery Runtime

HAL Recovery Runtime is a local-file, simulation-only runtime for validating HAL Recovery Compiler profiles and producing auditable dry-run artifacts.

> **Safety boundary:** This project does not control hardware, flash firmware, modify voltage or timing, execute real recovery, enforce real policy, perform real rollback, or claim certification.

HAL Recovery Runtime v1.0.0 is a public simulation-only proof of concept. It reads evidence, requires explicit review, and produces dry-run artifacts without controlling hardware.

## Current status

Version 1.0.0 freezes a stable public PoC contract for the documented CLI, artifact schemas, manual review workflow, safety invariants, and exit-code meanings. “Stable PoC” describes documented software semantics; it is not a production, fab, hardware-safety, or recovery claim.

Runtime v0.2.0 does not trust recovery_profile.json alone. It cross-checks the Compiler artifact bundle before producing a dry-run plan.

Runtime v0.2.1 distinguishes between a gate that failed and a gate that was never reached.

Runtime v0.3.0 introduces mock adapters only. A simulated adapter result is not a hardware action.

Runtime v0.3.1 makes adapter simulation auditable: every simulated, blocked, skipped, or invalid action must explain why.

Runtime v0.4.0 simulates failure and rollback logic only. A rollback plan is not a real rollback command.

Runtime v0.4.1 separates rollback from safe stop. A safe-stop marker is not a simulated revert.

Runtime v0.5.0 chooses simulated safety policy only. A policy decision is not permission to control hardware.

Runtime v0.5.1 explains policy decisions. The selected policy is determined by a deterministic simulation-only precedence order.

Runtime v0.6.0 bundles simulation evidence only. Hashes prove artifact integrity, not real hardware correctness.

Runtime v0.6.1 separates evidence validation failures. A hash mismatch is not an invalid JSON error.

Runtime v0.7.0 orchestrates the simulation chain only. A completed pipeline is not permission to control hardware.

Runtime v0.7.1 makes skipped and blocked pipeline stages explicit. A skipped evidence stage is not a successful evidence validation.

Runtime v0.8.0 reads chip/test data files only. A recovery profile candidate is not a hardware control profile.

Runtime v0.8.1 hardens shadow data quality semantics. A readable test file is not automatically reliable evidence.

Runtime v0.9.0 adds a review gate. A reviewed recovery profile is approved for dry-run simulation only, not hardware control.

Runtime v0.9.1 records review provenance. Promotion lineage proves artifact continuity, not hardware safety.

## What it does

- Reads bounded local CSV, JSON, and JSONL observations without device access.
- Explains shadow-data quality, field coverage, and conflicts.
- Builds a candidate profile that cannot contain assigned workloads.
- Requires an explicit review decision before dry-run-only promotion.
- Produces inert runtime plans, mock-adapter results, simulated rollback markers, policy explanations, evidence bundles, and pipeline reports.
- Validates the complete synthetic public PoC through internal Python functions.

## What it does not do

- No hardware execution, device control, firmware flashing, driver manipulation, voltage or timing control.
- No ATE, wafer-prober, oscilloscope, logic-analyzer, serial, USB, PCIe, SPI, I2C, GPIO, or network-device integration.
- No automatic remediation, promotion, workload deployment, pipeline handoff, production deployment, real rollback, or certification.
- No web server, database, GUI, remote service, dynamic adapter loading, or autonomous approval.

## Architecture

```text
Real chip/test files
        ↓ read-only
Shadow observations
        ↓ quality/conflict analysis
Recovery profile candidate
        ↓ explicit human review
Reviewed recovery profile
        ↓ simulation-only
Runtime dry-run / optional simulation pipeline
```

Every arrow is an explicit local-file operation. No stage authorizes hardware control.

## Public PoC workflow

The supported workflow has four phases:

1. Read-only observation: `ingest-shadow-data`, then `validate-shadow-data`.
2. Explicit review: `build-candidate-review`, then `validate-candidate-review` with a decision file.
3. Dry-run-only promotion: `promote-reviewed-profile`, `validate-profile`, then `dry-run`.
4. Optional simulation: `run-pipeline` and evidence validation.

Exact commands are in [docs/PUBLIC_POC_WORKFLOW.md](docs/PUBLIC_POC_WORKFLOW.md).

## Installation

Python 3.10 or newer is required.

```console
python -m pip install -e ".[test]"
```

The package has no runtime dependencies outside the Python standard library.

## CLI quick start

```console
hal-rr show-release-contract --out artifacts/release_contract
hal-rr validate-public-poc --out artifacts/public_poc_validation
hal-rr validate-profile samples/recovery_profile.json
hal-rr dry-run samples/recovery_profile.json --out artifacts/dry_run
```

The stable command list and argument reference are in [docs/CLI_REFERENCE.md](docs/CLI_REFERENCE.md).

Exit-code contract:

- `0`: valid input, completed simulation, non-blocking warnings, or pending review without promotion.
- `2`: invalid input, safety block, invalid decision/candidate/evidence, failed promotion, blocked pipeline, or invalid public PoC.
- `1`: unexpected internal failure, if surfaced.

## Artifact overview

Runtime, adapter, rollback, policy, evidence, pipeline, shadow, review, release-contract, and public-PoC artifacts all declare `runtime_version: 1.0.0` where applicable. Safety-bearing artifacts preserve `simulation_only: true`, `hardware_control_enabled: false`, and `claim_boundary: simulation_only_not_certified`.

The complete stable artifact table is in [docs/ARTIFACT_CONTRACT.md](docs/ARTIFACT_CONTRACT.md). No artifact authorizes hardware control.

## Review gate

The Compiler proposes and Runtime gates. A candidate remains unapproved until a separate decision file explicitly contains human approval, a non-empty reviewer ID and timestamp, `approved_for: dry_run_only`, and all required acknowledgements. Promotion writes SHA-256 lineage for artifact continuity only.

## Public PoC validation

```console
hal-rr validate-public-poc --example-root examples/public_poc --out artifacts/public_poc_validation
```

The command calls internal functions directly; it does not invoke a shell. It validates the synthetic example, release contract, shadow quality, review decision, promotion lineage, reviewed profile, dry-run, optional simulation pipeline, expected policy, and safety invariants.

## Reproducibility

```console
python -m pytest -q
python scripts/package_release.py
```

The release archive is `dist/hal-recovery-runtime-v1.0.0.zip`. ZIP entries use `/`, and caches, virtual environments, build output, installed-package metadata, and prior distribution contents are excluded. The public example uses fixed synthetic data and expected outputs.

## Security

Treat all input files as untrusted. Do not submit proprietary fab data or secrets, and do not connect this PoC to real hardware. See [SECURITY.md](SECURITY.md) and [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## Limitations

This PoC has no real fab validation, ATE integration, physical recovery proof, production reliability claim, cryptographic reviewer identity, or production security claim. Artifact integrity and review provenance do not prove physical chip recovery. See [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## License

MIT. See [LICENSE](LICENSE).

## Citation

Citation metadata is provided in [CITATION.cff](CITATION.cff). No DOI is assigned.
