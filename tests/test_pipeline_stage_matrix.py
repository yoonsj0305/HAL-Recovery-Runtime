import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


STAGES = {
    "input_load",
    "runtime_dry_run",
    "adapter_simulation",
    "failure_rollback_simulation",
    "policy_simulation",
    "evidence_bundle",
    "pipeline_report",
}


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage_matrix_includes_all_stages_and_matches_results(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    report = _read(tmp_path / "pipeline_report.json")
    assert result == EXIT_OK
    assert set(report["pipeline_stage_matrix"]) == STAGES
    for stage in report["stage_results"]:
        matrix = report["pipeline_stage_matrix"][stage["stage_name"]]
        assert matrix["status"] == stage["stage_status"]
        assert matrix["ran"] == stage["stage_ran"]
        assert matrix["skipped"] == stage["stage_skipped"]
        assert matrix["blocked"] == stage["stage_blocked"]
        assert matrix["failed"] == stage["stage_failed"]
        assert matrix["warning"] == stage["stage_warning"]


def test_blocked_runtime_and_no_evidence_are_reflected_in_matrix(tmp_path):
    blocked_dir = tmp_path / "blocked"
    noev_dir = tmp_path / "noev"
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/unsafe_hardware_enabled_profile.json",
                "--out",
                str(blocked_dir),
            ]
        )
        == EXIT_INVALID
    )
    assert (
        main(
            [
                "run-pipeline",
                "--profile",
                "samples/recovery_profile.json",
                "--no-evidence",
                "--out",
                str(noev_dir),
            ]
        )
        == EXIT_OK
    )

    blocked = _read(blocked_dir / "pipeline_report.json")["pipeline_stage_matrix"]
    noev = _read(noev_dir / "pipeline_report.json")["pipeline_stage_matrix"]
    assert blocked["runtime_dry_run"]["status"] == "blocked"
    assert blocked["evidence_bundle"]["status"] == "skipped"
    assert blocked["evidence_bundle"]["reason"] == "runtime_dry_run_blocked"
    assert noev["evidence_bundle"]["status"] == "skipped"
    assert noev["evidence_bundle"]["reason"] == "evidence_disabled"
