# Limitations

## Public PoC status

Version 1.0.0 freezes documented software semantics for a public proof of concept. It is not production-ready.

## Simulation-only boundary

All execution records are inert dry-run or mock-simulation artifacts.

## Synthetic-data limitation

The bundled example is deterministic synthetic data and does not represent a real wafer, die, device, or fab process.

## No real fab validation

No result establishes fab yield, recoverability, performance, reliability, or physical correctness.

## No ATE integration

The project has no ATE, wafer-prober, oscilloscope, logic-analyzer, or instrument interface.

## No hardware control

The project does not access device paths, buses, ports, firmware, drivers, voltage, timing, memory controllers, or operating-system schedulers.

## No certification

Reports and hashes are audit evidence, not safety, quality, compliance, or recovery certification.

## No automated workload deployment

Candidate and reviewed profiles contain no permission to deploy workloads. Promotion scope is dry-run-only.

## No production reliability claim

Passing tests or the synthetic workflow is not a production reliability guarantee.

## Shadow-data interpretation limits

Quality scores summarize input completeness and consistency. They do not infer physical safety or causality.

## Human-review limitations

Reviewer IDs and timestamps are recorded strings, not cryptographically verified identities or signatures.

## Hash and provenance limitations

SHA-256 detects byte-level change and records continuity; it does not establish truth, authorship, physical correctness, or safe recovery.

Artifact integrity and review provenance do not prove physical chip recovery.

## Security limitations

The PoC has bounded parsers and safety checks but makes no production-security claim. Inputs remain untrusted.

## Future work boundaries

Future work must not silently add hardware access, automatic approval, production deployment, real rollback, certification, or remote-service dependencies. Such changes require a separately reviewed project boundary.
