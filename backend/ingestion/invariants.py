from datetime import date
from decimal import Decimal

from ingestion.model import NetWorth

VALUE_TOL = Decimal("0.01")
UNIT_VALUE_TOL_RATE = Decimal("0.001")


def check_units_nav_consistency(nw: NetWorth) -> list[str]:
    problems = []
    for key, pos in nw.positions.items():
        if pos.units is None or pos.nav is None:
            continue
        expected = Decimal(pos.units) * Decimal(pos.nav)
        actual = Decimal(pos.value)
        tolerance = max(VALUE_TOL, abs(expected) * UNIT_VALUE_TOL_RATE)
        if abs(expected - actual) > tolerance:
            problems.append(
                f"{key}: units {pos.units} x nav {pos.nav} = {expected} != value {actual}"
            )
    return problems


def check_positions_sum_to_total(nw: NetWorth) -> list[str]:
    matching = [p for p in nw.positions.values() if p.currency == nw.reporting_currency]
    mismatched = [p for p in nw.positions.values() if p.currency != nw.reporting_currency]
    if mismatched:
        return [
            f"{len(mismatched)} position(s) in a currency other than reporting_currency "
            f"({nw.reporting_currency}) — sum-to-total check does not currency-convert "
            f"and was skipped"
        ]
    total = sum((Decimal(p.value) for p in matching), start=Decimal("0"))
    stated = Decimal(nw.total)
    if abs(total - stated) > VALUE_TOL:
        return [f"sum of positions {total} != stated total {stated}"]
    return []


def check_no_future_dates(nw: NetWorth, today: date | None = None) -> list[str]:
    today = today or date.today()
    problems = []
    for key, pos in nw.positions.items():
        if pos.as_of > today:
            problems.append(f"{key}: as_of {pos.as_of} is in the future (today={today})")
    if nw.as_of is not None and nw.as_of > today:
        problems.append(f"net worth as_of {nw.as_of} is in the future (today={today})")
    return problems


def check_account_name_prefixes(nw: NetWorth) -> list[str]:
    problems = []
    for key, pos in nw.positions.items():
        prefix = pos.account_name.split(":")[0]
        if prefix not in ("Assets", "Liabilities"):
            problems.append(
                f"{key}: account_name '{pos.account_name}' must start with "
                f"'Assets:' or 'Liabilities:'"
            )
        if key != pos.account_name:
            problems.append(
                f"position key '{key}' does not match its own account_name '{pos.account_name}'"
            )
    return problems


def check_invariants(nw: NetWorth, today: date | None = None) -> list[str]:
    problems: list[str] = []
    problems += check_units_nav_consistency(nw)
    problems += check_positions_sum_to_total(nw)
    problems += check_no_future_dates(nw, today=today)
    problems += check_account_name_prefixes(nw)
    return problems
