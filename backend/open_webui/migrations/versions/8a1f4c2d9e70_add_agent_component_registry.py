"""add agent component registry

Revision ID: 8a1f4c2d9e70
Revises: 5d7a9c1e2f30
Create Date: 2026-08-17 18:00:00.000000

This revision was previously applied in development. Keep it in the migration
history even though the Agent Configuration UI no longer exposes the component
registry. Applied Alembic revisions must remain resolvable.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '8a1f4c2d9e70'
down_revision: Union[str, None] = '5d7a9c1e2f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if 'agent_component_registry' in sa.inspect(conn).get_table_names():
        return
    op.create_table(
        'agent_component_registry',
        sa.Column('id', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Text(), nullable=False),
        sa.Column('manifest', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_component_registry_user', 'agent_component_registry', ['user_id'], unique=False)
    op.create_index('ix_agent_component_registry_updated', 'agent_component_registry', ['updated_at'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if 'agent_component_registry' not in sa.inspect(conn).get_table_names():
        return
    op.drop_index('ix_agent_component_registry_updated', table_name='agent_component_registry')
    op.drop_index('ix_agent_component_registry_user', table_name='agent_component_registry')
    op.drop_table('agent_component_registry')
