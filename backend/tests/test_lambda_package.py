import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
NOT_PACKAGED = {"seed_exchange_rates.py"}


def packaged_top_level_files() -> set[str]:
    script = (BACKEND / "scripts" / "build_lambda.sh").read_text()
    line = next(line for line in script.splitlines() if re.match(r"^cp app\.py ", line))
    return {name for name in line.split()[1:-1] if name.endswith(".py")}


def test_every_top_level_module_is_in_the_lambda_package():
    modules = {path.name for path in BACKEND.glob("*.py")} - NOT_PACKAGED

    assert modules - packaged_top_level_files() == set()


def test_the_package_lists_no_module_that_does_not_exist():
    assert {name for name in packaged_top_level_files() if not (BACKEND / name).exists()} == set()
