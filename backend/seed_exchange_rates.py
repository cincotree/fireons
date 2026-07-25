"""
Seed script to populate basic exchange rates for multi-currency support.
Run this once to add default rates.
"""
import asyncio
from datetime import date
from decimal import Decimal

from database.session import session_context
from database.repository import ExchangeRateRepository


async def seed_rates():
    """Add common exchange rates to the database."""
    async with session_context() as session:
        rate_repo = ExchangeRateRepository(session)

        # Current approximate rates (as of Feb 2025)
        rates = [
            # USD base rates
            ("USD", "INR", Decimal("83.0"), "2025-02-01"),
            ("USD", "EUR", Decimal("0.92"), "2025-02-01"),
            ("USD", "GBP", Decimal("0.79"), "2025-02-01"),

            # Add some historical rates for testing
            ("USD", "INR", Decimal("82.5"), "2025-01-01"),
            ("USD", "EUR", Decimal("0.91"), "2025-01-01"),
            ("USD", "GBP", Decimal("0.78"), "2025-01-01"),

            ("USD", "INR", Decimal("82.0"), "2024-12-01"),
            ("USD", "EUR", Decimal("0.90"), "2024-12-01"),
            ("USD", "GBP", Decimal("0.77"), "2024-12-01"),
        ]

        for from_curr, to_curr, rate, date_str in rates:
            rate_date = date.fromisoformat(date_str)
            await rate_repo.create_or_update(
                date=rate_date,
                from_currency=from_curr,
                to_currency=to_curr,
                rate=rate,
                source="seed_script",
            )
            print(f"✓ Added {from_curr}/{to_curr} = {rate} on {date_str}")

        print("\n✅ Exchange rates seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed_rates())
