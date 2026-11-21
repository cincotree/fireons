import ast
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


def packaged_directories() -> set[str]:
    script = (BACKEND / "scripts" / "build_lambda.sh").read_text()
    line = next(line for line in script.splitlines() if line.startswith("cp -R "))
    return set(line.split()[2:-1])


def imported_top_level_names(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_everything_the_packaged_code_imports_from_the_backend_is_packaged():
    files = [BACKEND / name for name in packaged_top_level_files()]
    files += [path for directory in packaged_directories() for path in (BACKEND / directory).rglob("*.py")]
    available = {name.removesuffix(".py") for name in packaged_top_level_files()} | packaged_directories()
    local = {path.stem for path in BACKEND.glob("*.py")} | {
        path.name for path in BACKEND.iterdir() if path.is_dir() and (path / "__init__.py").exists()
    }

    missing = {(path.name, name) for path in files for name in imported_top_level_names(path) & local - available}

    assert missing == set()
