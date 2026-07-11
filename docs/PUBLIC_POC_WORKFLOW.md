# Public PoC workflow

This workflow is manual, local-file-only, and simulation-only. The example data is synthetic.

## Step 1: read local observations

```console
hal-rr ingest-shadow-data examples/public_poc/input --out artifacts/public_poc/shadow
```

## Step 2: validate shadow artifacts

```console
hal-rr validate-shadow-data artifacts/public_poc/shadow --out artifacts/public_poc/shadow_validation
```

Inspect `shadow_quality_report.json`, its field coverage, quality band, and conflict matrix before continuing.

## Step 3: build the candidate review package

```console
hal-rr build-candidate-review artifacts/public_poc/shadow --out artifacts/public_poc/review
```

## Step 4: validate the explicit review decision

```console
hal-rr validate-candidate-review artifacts/public_poc/review --review-decision examples/public_poc/review_decision_approved.json --out artifacts/public_poc/review_validation
```

The review decision is explicit. Missing fields and template defaults never approve promotion.

## Step 5: promote for dry-run only

```console
hal-rr promote-reviewed-profile artifacts/public_poc/review --review-decision examples/public_poc/review_decision_approved.json --out artifacts/public_poc/promoted
```

Promotion is dry-run-only.

## Step 6: validate the reviewed profile

```console
hal-rr validate-profile artifacts/public_poc/promoted/reviewed_recovery_profile.json
```

## Step 7: execute the inert dry-run

```console
hal-rr dry-run artifacts/public_poc/promoted/reviewed_recovery_profile.json --out artifacts/public_poc/dry_run
```

## Step 8: optionally run the simulation pipeline

```console
hal-rr run-pipeline --profile artifacts/public_poc/promoted/reviewed_recovery_profile.json --out artifacts/public_poc/pipeline
```

Pipeline completion is not hardware permission. Hashes prove artifact continuity only. Synthetic example results do not prove fab performance. Every step reads or writes local files and remains simulation-only.

The same workflow can be checked without shell orchestration:

```console
hal-rr validate-public-poc --example-root examples/public_poc --out artifacts/public_poc_validation
```
