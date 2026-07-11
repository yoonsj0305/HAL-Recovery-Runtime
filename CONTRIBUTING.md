# Contributing

Contributions must preserve the simulation-only and local-file-only boundary.

1. Use synthetic data in tests and examples.
2. Do not add hardware SDKs, device paths, ports, remote services, shell orchestration, dynamic adapters, automatic approval, or automatic pipeline handoff.
3. Keep reasons and artifact ordering deterministic.
4. Add tests for valid, malformed, and safety-blocked paths.
5. Run `python -m pytest -q`, the forbidden-source scan, `validate-public-poc`, and the release ZIP audit before proposing a change.
6. Document any schema or CLI contract change explicitly.

Security-sensitive findings should follow [SECURITY.md](SECURITY.md), not a public pull request containing sensitive data.
