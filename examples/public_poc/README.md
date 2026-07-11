# Synthetic public PoC example

This directory contains only small, deterministic synthetic observations. It contains no proprietary fab data, personal data, device identifiers, or real hardware measurements.

The four synthetic tiles demonstrate one available tile, one blocked tile, one degraded tile, and one tile with conflicting observations. These records exercise evidence-quality and explicit-review behavior only. They do not demonstrate physical recovery or fab performance.

Run the full internal-function validation with:

```console
hal-rr validate-public-poc --example-root examples/public_poc --out artifacts/public_poc_validation
```

The approval file authorizes dry-run simulation only.
