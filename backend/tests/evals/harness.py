import itertools
import json
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from ingestion.model import NetWorth

EVALS_DIR = Path(__file__).parent
CASES_DIR = EVALS_DIR / "cases"


class EvalLoader(yaml.SafeLoader):
    pass


def _include_constructor(loader: yaml.SafeLoader, node: yaml.Node):
    rel_path = loader.construct_scalar(node)
    return json.loads((EVALS_DIR / rel_path).read_text())


EvalLoader.add_constructor("!include", _include_constructor)


def load_cases(layer: str | None = None):
    for path in sorted(CASES_DIR.glob("*.yaml")):
        cases = yaml.load(path.read_text(), Loader=EvalLoader)
        for case in cases:
            if layer is None or case["layer"] == layer:
                yield case


def _orderings(case: dict) -> list[list[Path]]:
    files = [EVALS_DIR / f for f in case["files"]]
    if not case.get("permute"):
        return [files]
    return [list(order) for order in dict.fromkeys(itertools.permutations(files))]


def params(layer: str):
    for case in load_cases(layer):
        orderings = _orderings(case)
        for i, order in enumerate(orderings):
            case_id = f"{case['id']}[{i}]" if len(orderings) > 1 else case["id"]
            yield pytest.param(case, order, id=case_id)


def canonical(nw: NetWorth | dict) -> dict:
    if isinstance(nw, dict):
        nw = NetWorth.model_validate(nw)
    positions = {}
    for key, pos in sorted(nw.positions.items()):
        positions[key] = {
            "value": str(Decimal(pos.value).quantize(Decimal("0.01"))),
            "currency": pos.currency,
            "as_of": pos.as_of.isoformat(),
            "units": (
                str(Decimal(pos.units).quantize(Decimal("0.001")))
                if pos.units is not None
                else None
            ),
        }
    return {
        "as_of": nw.as_of.isoformat() if nw.as_of else None,
        "reporting_currency": nw.reporting_currency,
        "positions": positions,
        "total": str(Decimal(nw.total).quantize(Decimal("0.01"))),
        "has_warnings": bool(nw.warnings),
    }


def diff(actual: dict, expected: dict) -> list[str]:
    out = []
    keys = set(actual["positions"]) | set(expected["positions"])
    for k in sorted(keys):
        a, e = actual["positions"].get(k), expected["positions"].get(k)
        if a is None:
            out.append(f"MISSING  {k}: expected {e}")
        elif e is None:
            out.append(f"EXTRA    {k}: got {a}")
        elif a != e:
            out.append(f"DRIFT    {k}: got {a} != expected {e}")
    if actual["total"] != expected["total"]:
        delta = Decimal(actual["total"]) - Decimal(expected["total"])
        out.append(f"TOTAL    delta {delta:+}")
    if actual["has_warnings"] != expected["has_warnings"]:
        out.append(
            f"WARNINGS expected presence={expected['has_warnings']}, "
            f"got presence={actual['has_warnings']}"
        )
    return out
