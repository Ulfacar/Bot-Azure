"""Seed Ton Azure hotel and backfill hotel_id=1 for all existing data

Revision ID: 008
Revises: 007
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём запись Hotel для Ton Azure (id=1)
    op.execute("""
        INSERT INTO hotels (id, name, slug, status, ai_model, created_at, updated_at)
        VALUES (
            1,
            'Тон Азур',
            'ton-azure',
            'active',
            'anthropic/claude-3.5-haiku',
            NOW(),
            NOW()
        )
    """)

    # Backfill hotel_id=1 для всех существующих записей
    op.execute("UPDATE clients SET hotel_id = 1 WHERE hotel_id IS NULL")
    op.execute("UPDATE conversations SET hotel_id = 1 WHERE hotel_id IS NULL")
    op.execute("UPDATE knowledge_base SET hotel_id = 1 WHERE hotel_id IS NULL")
    op.execute("UPDATE client_notes SET hotel_id = 1 WHERE hotel_id IS NULL")
    op.execute("UPDATE operators SET hotel_id = 1 WHERE hotel_id IS NULL")


def downgrade() -> None:
    op.execute("UPDATE clients SET hotel_id = NULL")
    op.execute("UPDATE conversations SET hotel_id = NULL")
    op.execute("UPDATE knowledge_base SET hotel_id = NULL")
    op.execute("UPDATE client_notes SET hotel_id = NULL")
    op.execute("UPDATE operators SET hotel_id = NULL")
    op.execute("DELETE FROM hotels WHERE id = 1")
