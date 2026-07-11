# Security policy

## Supported version

The supported public proof-of-concept line is 1.0.x. This support statement does not claim production security or hardware safety.

## Reporting a security issue

If this repository is hosted on GitHub with private vulnerability reporting enabled, use that private reporting channel. Otherwise, contact the repository maintainer through the repository's existing private contact mechanism. Do not include secrets, proprietary fab data, personal data, or live device information in a public issue.

Allow maintainers reasonable time to reproduce and address the issue before public disclosure. Provide the smallest synthetic reproducer possible.

## Safe use

- Treat every input file as untrusted.
- Do not submit proprietary fab data or secrets.
- Do not connect this PoC to real hardware or production systems.
- Do not use generated artifacts as hardware permission, certification, or a production-security decision.
- Prefer synthetic data when reporting parser, validation, or provenance issues.
