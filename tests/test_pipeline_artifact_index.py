import json
import re

from hal_runtime.cli import EXIT_OK, main


def test_pipeline_artifact_index_uses_relative_hashed_paths(tmp_path):
    result = main(
        [
            "run-pipeline",
            "--profile",
            "samples/recovery_profile.json",
            "--out",
            str(tmp_path),
        ]
    )

    index = json.loads((tmp_path / "pipeline_artifact_index.json").read_text(encoding="utf-8"))
    assert result == EXIT_OK
    assert index["hash_algorithm"] == "sha256"
    assert index["artifact_count"] == len(index["artifacts"])
    assert any(item["relative_path"] == "runtime/runtime_plan.json" for item in index["artifacts"])
    assert any(item["relative_path"] == "pipeline_report.json" for item in index["artifacts"])
    for item in index["artifacts"]:
        assert item["present"] is True
        assert not item["relative_path"].startswith("/")
        assert ":" not in item["relative_path"]
        assert "\\" not in item["relative_path"]
        assert not any(part.startswith(".") for part in item["relative_path"].split("/"))
        assert re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
        assert item["size_bytes"] > 0
