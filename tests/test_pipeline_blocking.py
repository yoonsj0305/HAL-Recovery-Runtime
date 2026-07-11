import json

from hal_runtime.cli import EXIT_INVALID, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _stage(report, name):
    return next(item for item in report["stage_results"] if item["stage_name"] == name)


def test_unsafe_profile_blocks_pipeline_and_skips_dependent_stages(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/unsafe_hardware_enabled_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    assert result == EXIT_INVALID
    assert report["pipeline_status"] == "pipeline_blocked"
    assert "blocked_by_safety_gate" in report["pipeline_blocking_reasons"]
    assert _stage(report, "runtime_dry_run")["stage_status"] == "blocked"
    assert _stage(report, "adapter_simulation")["stage_status"] == "skipped"
    assert _stage(report, "policy_simulation")["stage_status"] == "skipped"


def test_invalid_compiler_bundle_blocks_pipeline(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--bundle",
            "samples/compiler_bundle_mismatch_profile_id",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    assert result == EXIT_INVALID
    assert report["pipeline_status"] == "pipeline_blocked"
    assert "blocked_by_bundle_validation" in report["pipeline_blocking_reasons"]


def test_unsafe_policy_config_blocks_pipeline_after_prior_stages(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--policy-config",
            "samples/policy_config_unsafe_allow_real_execution.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    assert result == EXIT_INVALID
    assert report["pipeline_status"] == "pipeline_blocked"
    assert "blocked_policy_config_safety_boundary" in report["pipeline_blocking_reasons"]
    assert _stage(report, "runtime_dry_run")["stage_status"] == "completed"
    assert _stage(report, "policy_simulation")["stage_status"] == "blocked"
    assert _stage(report, "evidence_bundle")["stage_status"] == "skipped"
