"""add agentic workflow configuration

Revision ID: d7e8f9a0b1c2
Revises: c6b7d8e9f0a1
Create Date: 2026-08-18 18:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, None] = 'c6b7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'agentic_workflow_configuration' in inspector.get_table_names():
        return
    op.create_table(
        'agentic_workflow_configuration',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tool_name', sa.Text(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tool_name'),
    )
    op.create_index('ix_agentic_workflow_configuration_user_id', 'agentic_workflow_configuration', ['user_id'])
    op.create_index('ix_agentic_workflow_configuration_tool_name', 'agentic_workflow_configuration', ['tool_name'])
    op.create_index('ix_agentic_workflow_configuration_updated_at', 'agentic_workflow_configuration', ['updated_at'])


def downgrade() -> None:
    if 'agentic_workflow_configuration' in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table('agentic_workflow_configuration')
