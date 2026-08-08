from decimal import Decimal

import pytest

from ingestion.model import NetWorth
from ingestion.pipeline import ingest
from tests.evals.harness import canonical, diff, params

NOT_IMPLEMENTED = pytest.mark.xfail(
    raises=NotImplementedError,
    strict=True,
    reason="ingest() not yet implemented — Phase 1 covers the eval set only",
)


@NOT_IMPLEMENTED
@pytest.mark.parametrize("case,order", params("L1"))
def test_ledger_properties(case, order):
    seed = NetWorth.model_validate(case["current_nw"])
    result = ingest(seed, order)

    expected = canonical(case["expected_nw"])
    actual = canonical(result)

    problems = diff(actual, expected)
    assert not problems, f"\n{case['id']} — order {order}\n" + "\n".join(problems)


@NOT_IMPLEMENTED
@pytest.mark.parametrize("case,order", params("L1"))
def test_total_is_sum_of_positions(case, order):
    seed = NetWorth.model_validate(case["current_nw"])
    result = ingest(seed, order)

    matching = [p for p in result.positions.values() if p.currency == result.reporting_currency]
    total = sum((Decimal(p.value) for p in matching), start=Decimal("0"))
    assert abs(total - Decimal(result.total)) < Decimal("0.01"), (
        f"total {result.total} != sum of matching-currency positions {total}"
    )


@NOT_IMPLEMENTED
@pytest.mark.parametrize("case,order", params("L1"))
def test_second_ingest_is_noop(case, order):
    seed = NetWorth.model_validate(case["current_nw"])
    once = ingest(seed, order)
    twice = ingest(once, order)
    assert canonical(twice) == canonical(once)
