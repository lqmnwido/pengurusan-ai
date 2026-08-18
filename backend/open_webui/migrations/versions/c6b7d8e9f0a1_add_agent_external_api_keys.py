"""add agent external api keys

Revision ID: c6b7d8e9f0a1
Revises: 8a1f4c2d9e70
Create Date: 2026-08-18 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c6b7d8e9f0a1'
down_revision: Union[str, None] = '8a1f4c2d9e70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {column['name'] for column in sa.inspect(conn).get_columns('agent_configuration')}
    additions = (
        ('api_key_hash', sa.Text()),
        ('api_key_prefix', sa.Text()),
        ('api_key_created_at', sa.BigInteger()),
        ('api_key_last_used_at', sa.BigInteger()),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column('agent_configuration', sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    columns = {column['name'] for column in sa.inspect(conn).get_columns('agent_configuration')}
    for name in ('api_key_last_used_at', 'api_key_created_at', 'api_key_prefix', 'api_key_hash'):
        if name in columns:
            op.drop_column('agent_configuration', name)
