# Threat model

## Protected boundary

The protected property is that local untrusted inputs can produce only simulation artifacts and can never grant hardware permission, certification, automatic promotion, or automatic pipeline execution.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Malicious input JSON | Object-root checks, explicit schemas, safety-invariant validation |
| Malformed CSV or JSONL | Bounded readers, parse errors, deterministic invalid statuses |
| Oversized local files | Reader size limits and skipped-file reporting |
| Path traversal attempts | Fixed artifact names, basename-only source references, release ZIP path audit |
| Absolute-path leakage | Reports store basenames or relative artifact directories only |
| Unsafe review decision fields | Explicit decision validation matrix and fail-closed safety fields |
| Tampered candidate artifacts | SHA-256 review hashes and cross-artifact comparison |
| Tampered review decision | Decision SHA-256 provenance and explicit-file source |
| Hash mismatch | Deterministic artifact-integrity failure category |
| Hidden hardware-control fields | Recursive safety checks and forbidden-source guard |
| Misleading certification claims | Fixed claim boundary and certification-field blocks |
| Accidental automatic promotion | Promotion requires a separate explicit decision file and command |
| Accidental automatic pipeline execution | Shadow and review functions never invoke the pipeline |

Additional controls include local files only, no shell orchestration in the public PoC validator, no hardware SDKs, no dynamic adapters, fixed safety invariants, and deterministic trace records.
