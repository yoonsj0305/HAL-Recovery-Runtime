from hal_runtime.evidence_hasher import hash_with_size, sha256_file


def test_sha256_is_deterministic_and_records_size(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text('{"value":1}', encoding="utf-8")
    first = sha256_file(path)
    digest, size = hash_with_size(path)
    assert first == digest
    assert size == len(path.read_bytes())
    path.write_text('{"value":2}', encoding="utf-8")
    assert sha256_file(path) != first
