"""exchange rate history

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_exchange_rate_date_currencies', 'exchange_rates', type_='unique')
    op.create_index(
        'ix_exchange_rates_latest',
        'exchange_rates',
        ['from_currency', 'to_currency', 'date', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_exchange_rates_latest', table_name='exchange_rates')
    op.execute(
        """
        DELETE FROM exchange_rates a USING exchange_rates b
        WHERE a.date = b.date AND a.from_currency = b.from_currency
          AND a.to_currency = b.to_currency
          AND (a.created_at, a.id) < (b.created_at, b.id)
        """
    )
    op.create_unique_constraint(
        'uq_exchange_rate_date_currencies',
        'exchange_rates',
        ['date', 'from_currency', 'to_currency'],
    )
