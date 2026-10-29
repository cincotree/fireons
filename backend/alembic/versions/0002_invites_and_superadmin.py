"""invites and superadmin

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 20:33:09.024098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('invites',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=True),
    sa.Column('max_uses', sa.Integer(), nullable=False),
    sa.Column('use_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_by', sa.UUID(as_uuid=False), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invites_code_hash'), 'invites', ['code_hash'], unique=True)
    op.create_table('invite_redemptions',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('invite_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['invite_id'], ['invites.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_invite_redemptions_invite_id'), 'invite_redemptions', ['invite_id'], unique=False)
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('users', 'is_superadmin')
    op.drop_index(op.f('ix_invite_redemptions_invite_id'), table_name='invite_redemptions')
    op.drop_table('invite_redemptions')
    op.drop_index(op.f('ix_invites_code_hash'), table_name='invites')
    op.drop_table('invites')
