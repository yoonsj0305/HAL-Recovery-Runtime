# Stable v1.0.0 CLI reference

All commands operate on local files and remain simulation-only.

## Core Runtime

- `validate-profile PROFILE`
- `check-compat PROFILE`
- `plan PROFILE --out DIR`
- `dry-run PROFILE --out DIR`

## Compiler bundle

- `validate-bundle BUNDLE [--out DIR]`
- `dry-run-bundle BUNDLE --out DIR`

## Simulation

- `list-adapters [--out DIR]`
- `simulate-plan PLAN --out DIR`
- `list-failure-modes [--out DIR]`
- `simulate-failure PLAN [--scenario FILE] --out DIR`
- `list-policies [--out DIR]`
- `simulate-policy PLAN [--adapter-report FILE] [--rollback-report FILE] [--policy-config FILE] --out DIR`

## Evidence

- `list-evidence-schema [--out DIR]`
- `build-evidence-bundle SOURCE --out DIR`
- `validate-evidence-bundle BUNDLE --out DIR`

## Pipeline

- `list-pipeline-stages [--out DIR]`
- `run-pipeline (--profile FILE | --bundle DIR) [--failure-scenario FILE] [--policy-config FILE] [--stop-on-warning] [--no-evidence] --out DIR`

## Shadow ingestion

- `list-shadow-schemas [--out DIR]`
- `ingest-shadow-data SOURCE --out DIR`
- `validate-shadow-data SOURCE --out DIR`

## Review gate

- `list-review-gates [--out DIR]`
- `build-candidate-review SOURCE --out DIR`
- `validate-candidate-review SOURCE [--review-decision FILE] --out DIR`
- `promote-reviewed-profile SOURCE --review-decision FILE --out DIR`

## Release contract

- `show-release-contract [--out DIR]`
- `validate-public-poc [--example-root DIR] --out DIR`

## Exit codes

- `0`: valid input, completed simulation-only operation, non-blocking warning, or pending review when promotion was not requested.
- `2`: invalid input, safety boundary block, invalid review decision or candidate, invalid evidence, failed promotion, blocked pipeline, or invalid public PoC.
- `1`: unexpected internal failure only, if surfaced.

No command automatically promotes a candidate, starts a pipeline from shadow ingestion, deploys workloads, or controls hardware.
