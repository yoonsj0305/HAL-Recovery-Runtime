# Stable artifact contract

Required safety fields are `simulation_only: true`, `hardware_control_enabled: false`, and `claim_boundary: simulation_only_not_certified` unless an older external input format does not own those fields. Stability means documented public-PoC semantics, not production or hardware stability.

| Artifact | Producing command | Purpose | Direction | Required safety fields | Can trigger execution? | Stability | Hardware authority |
|---|---|---|---|---|---|---|---|
| `runtime_plan.json` | `plan`, `dry-run` | Inert action plan | input/output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `runtime_report.json` | `dry-run` | Safety-gate and dry-run result | output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `adapter_report.json` | `simulate-plan` | Mock-adapter audit | input/output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `rollback_report.json` | `simulate-failure` | Simulated revert/safe-stop explanation | input/output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `policy_report.json` | `simulate-policy` | Deterministic simulated policy explanation | input/output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `evidence_report.json` | `build-evidence-bundle` | Evidence inventory and integrity summary | input/output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `pipeline_report.json` | `run-pipeline` | Simulation-pipeline stage result | output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `shadow_observations.json` | `ingest-shadow-data` | Normalized read-only observations | input/output | Required plus `read_only: true` | No | stable PoC | No artifact authorizes hardware control. |
| `shadow_quality_report.json` | `ingest-shadow-data` | Quality, coverage, and conflict explanation | input/output | Required plus `read_only: true` | No | stable PoC | No artifact authorizes hardware control. |
| `recovery_profile_candidate.json` | `ingest-shadow-data` | Human-review candidate | input/output | Required plus `hardware_execution_enabled: false` | No | stable PoC | No artifact authorizes hardware control. |
| `candidate_review_package.json` | `build-candidate-review` | Candidate snapshot, gates, and source hashes | input/output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `candidate_review_report.json` | `build-candidate-review` | Candidate review result | input/output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `reviewed_recovery_profile.json` | `promote-reviewed-profile` | Reviewed dry-run-only profile | input/output | Required plus `hardware_execution_enabled: false` | Simulation only when separately passed to a command | stable PoC | No artifact authorizes hardware control. |
| `profile_promotion_report.json` | `promote-reviewed-profile` | Explicit decision, preflight, and lineage result | output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `release_contract.json` | `show-release-contract` | Stable CLI, artifact, workflow, safety, and exit-code contract | output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `public_poc_report.json` | `validate-public-poc` | Synthetic end-to-end workflow summary | output | Required | No | stable PoC | No artifact authorizes hardware control. |
| `public_poc_validation_report.json` | `validate-public-poc` | Public-PoC validation matrix | output | Required | No | stable PoC | No artifact authorizes hardware control. |

Artifacts are passive local files. A later explicit simulation command may read a compatible artifact, but no artifact initiates a process, pipeline, promotion, device action, or deployment by itself.
