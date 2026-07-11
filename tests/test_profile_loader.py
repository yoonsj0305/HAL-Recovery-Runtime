import json

import pytest

from hal_runtime.profile_loader import ProfileLoadError, load_profile


def test_loads_valid_profile(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"profile_id": "P1"}), encoding="utf-8")

    assert load_profile(path)["profile_id"] == "P1"


def test_missing_file_fails_cleanly(tmp_path):
    with pytest.raises(ProfileLoadError, match="profile_not_readable"):
        load_profile(tmp_path / "missing.json")


def test_invalid_json_fails_cleanly(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ProfileLoadError, match="profile_invalid_json"):
        load_profile(path)


def test_non_object_root_fails_cleanly(tmp_path):
    path = tmp_path / "list.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ProfileLoadError, match="profile_root_must_be_object"):
        load_profile(path)

