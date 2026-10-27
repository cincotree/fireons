from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('professional_websites',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('professional_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('domain', sa.String(length=255), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('derived_from', sa.String(length=50), nullable=False),
    sa.Column('check_status', sa.String(length=30), nullable=False),
    sa.Column('pages_checked', sa.Integer(), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['professional_id'], ['financial_professionals.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('professional_id', 'domain', name='uq_website_professional_domain')
    )
    op.create_index('ix_websites_last_checked', 'professional_websites', ['last_checked_at'], unique=False)
    op.create_table('nri_signals',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('website_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('professional_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('page_url', sa.Text(), nullable=False),
    sa.Column('signal_type', sa.String(length=50), nullable=False),
    sa.Column('matched_text', sa.Text(), nullable=False),
    sa.Column('text_hash', sa.String(length=64), nullable=False),
    sa.Column('location', sa.String(length=30), nullable=False),
    sa.Column('confidence', sa.String(length=10), nullable=False),
    sa.Column('review_status', sa.String(length=20), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['professional_id'], ['financial_professionals.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['website_id'], ['professional_websites.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('website_id', 'page_url', 'signal_type', 'text_hash', name='uq_signal_identity')
    )
    op.create_index('ix_nri_signals_professional', 'nri_signals', ['professional_id'], unique=False)
    op.create_index('ix_nri_signals_review', 'nri_signals', ['review_status', 'confidence'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_nri_signals_review', table_name='nri_signals')
    op.drop_index('ix_nri_signals_professional', table_name='nri_signals')
    op.drop_table('nri_signals')
    op.drop_index('ix_websites_last_checked', table_name='professional_websites')
    op.drop_table('professional_websites')
