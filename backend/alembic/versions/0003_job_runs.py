"""job_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('job_runs',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('job', sa.String(length=100), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', name='jobrunstatus'), nullable=False),
    sa.Column('task_arn', sa.String(length=255), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_job_runs_job_created_at', 'job_runs', ['job', 'created_at'], unique=False)
    op.create_index('ix_job_runs_status', 'job_runs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_job_runs_status', table_name='job_runs')
    op.drop_index('ix_job_runs_job_created_at', table_name='job_runs')
    op.drop_table('job_runs')
    sa.Enum(name='jobrunstatus').drop(op.get_bind(), checkfirst=True)
