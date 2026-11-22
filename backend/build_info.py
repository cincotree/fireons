import json
from functools import lru_cache
from pathlib import Path

DEFAULT_PATH = Path(__file__).parent / "build_info.json"
UNBUILT = {"version": "dev", "built_at": None}


def load_build_info(path: Path) -> dict:
    if not path.exists():
        return dict(UNBUILT)
    return json.loads(path.read_text())


@lru_cache
def get_build_info() -> dict:
    return load_build_info(DEFAULT_PATH)
