from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0010'
down_revision: Union[str, Sequence[str], None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'consent_records',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('purpose', sa.String(length=50), nullable=False),
        sa.Column('notice_version', sa.String(length=20), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_consent_records_user_purpose_created',
        'consent_records',
        ['user_id', 'purpose', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_consent_records_user_purpose_created', table_name='consent_records')
    op.drop_table('consent_records')
