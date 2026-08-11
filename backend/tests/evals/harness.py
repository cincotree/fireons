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


# Numeric tolerance for position/total comparison. This does NOT relax key
# matching — account_name is still compared exactly, on purpose (see
# ingestion/pipeline.py: keys must be built deterministically from stable
# identifiers, not generated as free text, precisely so exact key matching
# stays meaningful once ingest() is LLM-backed). This only absorbs harmless
# precision/formatting noise in the numeric fields once a real extraction
# is under test, not just the current stub.
VALUE_TOL = Decimal("0.01")
UNIT_TOL = Decimal("0.001")


def _position_diff(a: dict, e: dict) -> list[str]:
    problems = []
    if a["currency"] != e["currency"]:
        problems.append(f"currency: got {a['currency']} != expected {e['currency']}")
    if a["as_of"] != e["as_of"]:
        problems.append(f"as_of: got {a['as_of']} != expected {e['as_of']}")
    if abs(Decimal(a["value"]) - Decimal(e["value"])) > VALUE_TOL:
        problems.append(f"value: got {a['value']} != expected {e['value']}")
    if (a["units"] is None) != (e["units"] is None):
        problems.append(f"units: got {a['units']} != expected {e['units']}")
    elif a["units"] is not None and abs(Decimal(a["units"]) - Decimal(e["units"])) > UNIT_TOL:
        problems.append(f"units: got {a['units']} != expected {e['units']}")
    return problems


def diff(actual: dict, expected: dict) -> list[str]:
    out = []
    keys = set(actual["positions"]) | set(expected["positions"])
    for k in sorted(keys):
        a, e = actual["positions"].get(k), expected["positions"].get(k)
        if a is None:
            out.append(f"MISSING  {k}: expected {e}")
        elif e is None:
            out.append(f"EXTRA    {k}: got {a}")
        else:
            field_problems = _position_diff(a, e)
            if field_problems:
                out.append(f"DRIFT    {k}: " + "; ".join(field_problems))
    if abs(Decimal(actual["total"]) - Decimal(expected["total"])) > VALUE_TOL:
        delta = Decimal(actual["total"]) - Decimal(expected["total"])
        out.append(f"TOTAL    delta {delta:+}")
    if actual["has_warnings"] != expected["has_warnings"]:
        out.append(
            f"WARNINGS expected presence={expected['has_warnings']}, "
            f"got presence={actual['has_warnings']}"
        )
    return out
