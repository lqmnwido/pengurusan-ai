"""add agent configuration table

Revision ID: 5d7a9c1e2f30
Revises: 461111b60977
Create Date: 2026-08-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '5d7a9c1e2f30'
down_revision: Union[str, None] = '461111b60977'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'agent_configuration' in inspector.get_table_names():
        return

    op.create_table(
        'agent_configuration',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('code_path', sa.Text(), nullable=True),
        sa.Column('code_filename', sa.Text(), nullable=True),
        sa.Column('code_sha256', sa.Text(), nullable=True),
        sa.Column('code_validation', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_configuration_user', 'agent_configuration', ['user_id'], unique=False)
    op.create_index('ix_agent_configuration_updated', 'agent_configuration', ['updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_agent_configuration_updated', table_name='agent_configuration')
    op.drop_index('ix_agent_configuration_user', table_name='agent_configuration')
    op.drop_table('agent_configuration')
