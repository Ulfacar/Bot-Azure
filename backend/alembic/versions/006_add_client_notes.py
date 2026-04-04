"""Add client_notes table

Revision ID: 006
Revises: 005
Create Date: 2026-04-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'client_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(50), nullable=False, index=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('added_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['added_by_id'], ['operators.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('client_notes')
