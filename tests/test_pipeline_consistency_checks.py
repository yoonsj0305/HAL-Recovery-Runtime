import json

from hal_runtime.cli import EXIT_INVALID, EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_consistency(path):
    report = _read(path / "pipeline_report.json")
    assert all(report["pipeline_consistency_checks"].values())
    counts = report["stage_counts"]
    stage_results = report["stage_results"]
    assert counts["total_stages"] == len(stage_results) == 7
    for status in ("completed", "completed_with_warnings", "skipped", "blocked", "failed"):
        assert counts[status] == sum(stage["stage_status"] == status for stage in stage_results)
    index = _read(path / "pipeline_artifact_index.json")
    assert all(not item["relative_path"].startswith("/") for item in index["artifacts"])
    assert all("\\" not in item["relative_path"] for item in index["artifacts"])


def test_consistency_checks_true_for_normal_blocked_and_no_evidence_runs(tmp_path):
    normal = tmp_path / "normal"
    blocked = tmp_path / "blocked"
    noev = tmp_path / "noev"
    assert main(["run-pipeline", "--profile", "samples/recovery_profile.json", "--out", str(normal)]) == EXIT_OK
    assert main(["run-pipeline", "--profile", "samples/unsafe_hardware_enabled_profile.json", "--out", str(blocked)]) == EXIT_INVALID
    assert main(["run-pipeline", "--profile", "samples/recovery_profile.json", "--no-evidence", "--out", str(noev)]) == EXIT_OK
    _assert_consistency(normal)
    _assert_consistency(blocked)
    _assert_consistency(noev)
