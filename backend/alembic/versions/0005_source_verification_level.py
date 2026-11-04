from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('data_sources', sa.Column('verification_level', sa.String(length=20), server_default='verified', nullable=False))


def downgrade() -> None:
    op.drop_column('data_sources', 'verification_level')
