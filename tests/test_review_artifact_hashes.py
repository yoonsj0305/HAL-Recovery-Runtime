import json

from hal_runtime.cli import EXIT_OK, main


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_review_hashes_are_complete_local_and_change_with_source(tmp_path):
    shadow, review1, review2 = (tmp_path / name for name in ("shadow", "review1", "review2"))
    assert main(["ingest-shadow-data", "samples/shadow_input_valid", "--out", str(shadow)]) == EXIT_OK
    assert main(["build-candidate-review", str(shadow), "--out", str(review1)]) == EXIT_OK
    package1 = _read(review1 / "candidate_review_package.json")
    report1 = _read(review1 / "candidate_review_report.json")
    hashes1 = package1["review_artifact_hashes"]
    assert hashes1 == report1["review_artifact_hashes"]
    assert all("/" not in name and "\\" not in name for name in hashes1)
    assert hashes1["shadow_validation_report.json"]["present"] is False
    assert all(len(record["sha256"]) == 64 for record in hashes1.values() if record["present"])
    candidate_path = shadow / "recovery_profile_candidate.json"
    candidate = _read(candidate_path)
    candidate["test_hash_change_marker"] = True
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    assert main(["build-candidate-review", str(shadow), "--out", str(review2)]) == EXIT_OK
    hashes2 = _read(review2 / "candidate_review_package.json")["review_artifact_hashes"]
    assert hashes1["recovery_profile_candidate.json"]["sha256"] != hashes2["recovery_profile_candidate.json"]["sha256"]

