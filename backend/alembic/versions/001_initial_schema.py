"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('primary_currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    op.create_table(
        'accounts',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('account_type', sa.Enum('ASSETS', 'LIABILITIES', 'EQUITY', 'INCOME', 'EXPENSES', name='accounttype'), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('open_date', sa.Date(), nullable=False),
        sa.Column('close_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('meta', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'name', name='uq_account_user_name'),
    )
    op.create_index('ix_accounts_name', 'accounts', ['name'])
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'])

    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('flag', sa.String(1), nullable=False, server_default='*'),
        sa.Column('payee', sa.String(500), nullable=True),
        sa.Column('narration', sa.Text(), nullable=False),
        sa.Column('meta', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_date', 'transactions', ['date'])
    op.create_index('ix_transactions_payee', 'transactions', ['payee'])
    op.create_index('ix_transactions_date_payee', 'transactions', ['date', 'payee'])

    op.create_table(
        'postings',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('amount', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('cost_amount', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('cost_currency', sa.String(10), nullable=True),
        sa.Column('cost_date', sa.Date(), nullable=True),
        sa.Column('price_amount', sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column('price_currency', sa.String(10), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_postings_transaction_id', 'postings', ['transaction_id'])
    op.create_index('ix_postings_account_id', 'postings', ['account_id'])

    op.create_table(
        'balances',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('account_id', 'date', 'currency', name='uq_balance_account_date_currency'),
    )
    op.create_index('ix_balances_account_date', 'balances', ['account_id', 'date'])

    op.create_table(
        'exchange_rates',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('from_currency', sa.String(10), nullable=False),
        sa.Column('to_currency', sa.String(10), nullable=False),
        sa.Column('rate', sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('date', 'from_currency', 'to_currency', name='uq_exchange_rate_date_currencies'),
    )
    op.create_index('ix_exchange_rates_date', 'exchange_rates', ['date'])
    op.create_index('ix_exchange_rates_from_currency', 'exchange_rates', ['from_currency'])
    op.create_index('ix_exchange_rates_to_currency', 'exchange_rates', ['to_currency'])
    op.create_index('ix_exchange_rates_currencies', 'exchange_rates', ['from_currency', 'to_currency'])

    op.create_table(
        'transaction_links',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('link', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('transaction_id', 'link', name='uq_transaction_link'),
    )
    op.create_index('ix_transaction_links_link', 'transaction_links', ['link'])

    op.create_table(
        'transaction_tags',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('tag', sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('transaction_id', 'tag', name='uq_transaction_tag'),
    )
    op.create_index('ix_transaction_tags_tag', 'transaction_tags', ['tag'])


def downgrade() -> None:
    op.drop_table('transaction_tags')
    op.drop_table('transaction_links')
    op.drop_table('exchange_rates')
    op.drop_table('balances')
    op.drop_table('postings')
    op.drop_table('transactions')
    op.drop_table('accounts')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS accounttype')
