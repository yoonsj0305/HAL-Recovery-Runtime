import csv
import json
from pathlib import Path


ROOT = Path("examples/public_poc")


def test_public_example_is_small_synthetic_and_has_expected_contract():
    rows = list(csv.DictReader((ROOT / "input" / "test_log.csv").open(encoding="utf-8")))
    extra = json.loads((ROOT / "input" / "tile_status.json").read_text(encoding="utf-8"))["observations"]
    assert {row["profile_id"] for row in rows} == {"PUBLIC_POC_PROFILE_001"}
    assert len({row["tile_id"] for row in rows}) == 4
    assert {"pass", "fail", "degraded"} <= {row["observed_status"] for row in rows}
    assert extra[0]["tile_id"] == "POC_TILE_03"
    assert extra[0]["observed_status"] == "fail"
    assert "synthetic" in (ROOT / "README.md").read_text(encoding="utf-8").lower()
    expected = json.loads((ROOT / "expected" / "expected_safety_invariants.json").read_text(encoding="utf-8"))
    assert expected == {
        "simulation_only": True,
        "hardware_control_enabled": False,
        "hardware_execution_enabled": False,
        "claim_boundary": "simulation_only_not_certified",
        "approved_for": "dry_run_only",
    }

