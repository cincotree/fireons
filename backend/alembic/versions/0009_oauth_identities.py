from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=True)
    op.drop_column('users', 'hashed_password')
    op.create_table(
        'oauth_identities',
        sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_subject'),
    )
    op.create_index(op.f('ix_oauth_identities_user_id'), 'oauth_identities', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_oauth_identities_user_id'), table_name='oauth_identities')
    op.drop_table('oauth_identities')
    op.add_column('users', sa.Column('hashed_password', sa.String(length=255), server_default='', nullable=False))
    op.alter_column('users', 'hashed_password', server_default=None)
    op.alter_column('users', 'email', existing_type=sa.String(length=255), nullable=False)
