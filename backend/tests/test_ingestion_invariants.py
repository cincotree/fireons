from datetime import date, timedelta

import pytest

from ingestion.invariants import (
    check_account_name_prefixes,
    check_invariants,
    check_no_future_dates,
    check_positions_sum_to_total,
    check_units_nav_consistency,
)
from ingestion.model import NetWorth, Position


def _mf_position(
    account_name: str = "Assets:Investment:MutualFund:SampleAMC1:FOLIO001:SchemeAlpha",
    units: str = "100.000",
    nav: str = "50.0000",
    value: str = "5000.00",
    as_of: date = date(2026, 7, 31),
) -> Position:
    return Position(
        account_name=account_name,
        units=units,
        nav=nav,
        value=value,
        currency="INR",
        as_of=as_of,
    )


def _bank_position(
    account_name: str = "Assets:Bank:HDFC:6789",
    value: str = "150000.00",
    as_of: date = date(2026, 7, 31),
) -> Position:
    return Position(account_name=account_name, value=value, currency="INR", as_of=as_of)


class TestUnitsNavConsistency:
    def test_consistent_position_has_no_problems(self):
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={"Assets:Investment:MutualFund:SampleAMC1:FOLIO001:SchemeAlpha": _mf_position()},
            total="5000.00",
        )
        assert check_units_nav_consistency(nw) == []

    def test_mismatched_units_times_nav_is_flagged(self):
        bad = _mf_position(value="9999.00")
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={bad.account_name: bad},
            total="9999.00",
        )
        problems = check_units_nav_consistency(nw)
        assert len(problems) == 1
        assert "9999.00" in problems[0]

    def test_bank_position_without_units_or_nav_is_skipped(self):
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={"Assets:Bank:HDFC:6789": _bank_position()},
            total="150000.00",
        )
        assert check_units_nav_consistency(nw) == []


class TestPositionsSumToTotal:
    def test_matching_sum_has_no_problems(self):
        mf = _mf_position()
        bank = _bank_position()
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={mf.account_name: mf, bank.account_name: bank},
            total="155000.00",
        )
        assert check_positions_sum_to_total(nw) == []

    def test_mismatched_total_is_flagged(self):
        bank = _bank_position()
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={bank.account_name: bank},
            total="999999.00",
        )
        problems = check_positions_sum_to_total(nw)
        assert len(problems) == 1
        assert "999999.00" in problems[0]

    def test_mixed_currency_positions_are_flagged_and_skipped_rather_than_summed(self):
        inr_position = _bank_position()
        usd_position = _bank_position(account_name="Assets:Bank:Chase:1234", value="1000.00")
        usd_position = usd_position.model_copy(update={"currency": "USD"})
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={inr_position.account_name: inr_position, usd_position.account_name: usd_position},
            total="150000.00",
        )
        problems = check_positions_sum_to_total(nw)
        assert len(problems) == 1
        assert "currency other than reporting_currency" in problems[0]


class TestNoFutureDates:
    def test_present_and_past_dates_have_no_problems(self):
        bank = _bank_position(as_of=date.today() - timedelta(days=1))
        nw = NetWorth(
            as_of=date.today(),
            reporting_currency="INR",
            positions={bank.account_name: bank},
            total="150000.00",
        )
        assert check_no_future_dates(nw) == []

    def test_future_position_date_is_flagged(self):
        future = date.today() + timedelta(days=30)
        bank = _bank_position(as_of=future)
        nw = NetWorth(
            as_of=date.today(),
            reporting_currency="INR",
            positions={bank.account_name: bank},
            total="150000.00",
        )
        problems = check_no_future_dates(nw)
        assert len(problems) == 1
        assert str(future) in problems[0]


class TestAccountNamePrefixes:
    def test_valid_prefixes_have_no_problems(self):
        bank = _bank_position()
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={bank.account_name: bank},
            total="150000.00",
        )
        assert check_account_name_prefixes(nw) == []

    def test_invalid_prefix_is_flagged(self):
        bad = _bank_position(account_name="Income:Salary")
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={"Income:Salary": bad},
            total="150000.00",
        )
        problems = check_account_name_prefixes(nw)
        assert any("must start with" in p for p in problems)

    def test_key_mismatched_with_account_name_is_flagged(self):
        bank = _bank_position()
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={"Assets:Bank:HDFC:0000": bank},
            total="150000.00",
        )
        problems = check_account_name_prefixes(nw)
        assert any("does not match its own account_name" in p for p in problems)


class TestCheckInvariants:
    def test_clean_net_worth_has_no_problems(self):
        mf = _mf_position()
        bank = _bank_position()
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={mf.account_name: mf, bank.account_name: bank},
            total="155000.00",
        )
        assert check_invariants(nw, today=date(2026, 7, 31)) == []

    def test_aggregates_problems_from_every_check(self):
        bad_units = _mf_position(value="1.00")
        nw = NetWorth(
            as_of=date(2026, 7, 31),
            reporting_currency="INR",
            positions={bad_units.account_name: bad_units},
            total="999.00",
        )
        problems = check_invariants(nw, today=date(2026, 7, 31))
        assert len(problems) >= 2
