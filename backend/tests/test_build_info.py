import json

from build_info import UNBUILT, load_build_info


def test_missing_file_reports_a_dev_build(tmp_path):
    assert load_build_info(tmp_path / "build_info.json") == UNBUILT


def test_build_info_is_read_from_the_file(tmp_path):
    path = tmp_path / "build_info.json"
    path.write_text(json.dumps({"version": "abc123", "built_at": "2026-10-31T05:00:00Z"}))

    assert load_build_info(path) == {"version": "abc123", "built_at": "2026-10-31T05:00:00Z"}


def test_unbuilt_default_is_not_shared_between_calls(tmp_path):
    first = load_build_info(tmp_path / "missing.json")
    first["version"] = "changed"

    assert load_build_info(tmp_path / "missing.json")["version"] == "dev"
