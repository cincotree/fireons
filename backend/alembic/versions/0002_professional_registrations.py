from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table('data_sources',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('regulator', sa.String(length=100), nullable=False),
    sa.Column('default_profession_type', sa.String(length=100), nullable=False),
    sa.Column('base_url', sa.Text(), nullable=False),
    sa.Column('is_enabled', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('financial_professionals',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('display_name', sa.String(length=500), nullable=False),
    sa.Column('name_normalized', sa.String(length=500), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_financial_professionals_name_trgm', 'financial_professionals', ['name_normalized'], unique=False, postgresql_using='gin', postgresql_ops={'name_normalized': 'gin_trgm_ops'})
    op.create_table('professional_registrations',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('professional_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('source_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('profession_type', sa.String(length=100), nullable=False),
    sa.Column('registration_number', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=True),
    sa.Column('valid_until', sa.Date(), nullable=True),
    sa.Column('validity_raw', sa.Text(), nullable=True),
    sa.Column('city', sa.String(length=255), nullable=True),
    sa.Column('state', sa.String(length=255), nullable=True),
    sa.Column('pincode', sa.String(length=10), nullable=True),
    sa.Column('address_raw', sa.Text(), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('contact_person', sa.String(length=500), nullable=True),
    sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('source_url', sa.Text(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_changed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('missing_runs', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['professional_id'], ['financial_professionals.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_id', 'registration_number', name='uq_registration_source_number')
    )
    op.create_index('ix_registrations_professional', 'professional_registrations', ['professional_id'], unique=False)
    op.create_index('ix_registrations_state_city', 'professional_registrations', ['state', 'city'], unique=False)
    op.create_index('ix_registrations_type_status', 'professional_registrations', ['profession_type', 'status'], unique=False)
    op.create_table('scrape_runs',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('source_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('trigger', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expected_total', sa.Integer(), nullable=True),
    sa.Column('pages_fetched', sa.Integer(), nullable=False),
    sa.Column('records_seen', sa.Integer(), nullable=False),
    sa.Column('inserted', sa.Integer(), nullable=False),
    sa.Column('updated', sa.Integer(), nullable=False),
    sa.Column('unchanged', sa.Integer(), nullable=False),
    sa.Column('parse_errors', sa.Integer(), nullable=False),
    sa.Column('marked_delisted', sa.Integer(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['source_id'], ['data_sources.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_scrape_runs_source_started', 'scrape_runs', ['source_id', 'started_at'], unique=False)
    op.create_table('registration_versions',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('registration_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('run_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['registration_id'], ['professional_registrations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['run_id'], ['scrape_runs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('registration_id', 'run_id', name='uq_version_registration_run')
    )
    op.create_index('ix_versions_registration_scraped', 'registration_versions', ['registration_id', 'scraped_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_versions_registration_scraped', table_name='registration_versions')
    op.drop_table('registration_versions')
    op.drop_index('ix_scrape_runs_source_started', table_name='scrape_runs')
    op.drop_table('scrape_runs')
    op.drop_index('ix_registrations_type_status', table_name='professional_registrations')
    op.drop_index('ix_registrations_state_city', table_name='professional_registrations')
    op.drop_index('ix_registrations_professional', table_name='professional_registrations')
    op.drop_table('professional_registrations')
    op.drop_index('ix_financial_professionals_name_trgm', table_name='financial_professionals', postgresql_using='gin', postgresql_ops={'name_normalized': 'gin_trgm_ops'})
    op.drop_table('financial_professionals')
    op.drop_table('data_sources')
