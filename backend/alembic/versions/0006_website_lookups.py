from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'website_lookups',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('professional_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('method', sa.String(length=30), nullable=True),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['professional_id'], ['financial_professionals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('professional_id'),
    )


def downgrade() -> None:
    op.drop_table('website_lookups')
