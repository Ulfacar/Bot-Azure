"""Enforce hotel_id NOT NULL + FK constraints + indexes

Revision ID: 009
Revises: 008
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NOT NULL constraints
    op.alter_column('clients', 'hotel_id', nullable=False)
    op.alter_column('conversations', 'hotel_id', nullable=False)
    op.alter_column('knowledge_base', 'hotel_id', nullable=False)
    op.alter_column('client_notes', 'hotel_id', nullable=False)
    op.alter_column('operators', 'hotel_id', nullable=False)

    # Foreign key constraints
    op.create_foreign_key('fk_clients_hotel_id', 'clients', 'hotels', ['hotel_id'], ['id'])
    op.create_foreign_key('fk_conversations_hotel_id', 'conversations', 'hotels', ['hotel_id'], ['id'])
    op.create_foreign_key('fk_knowledge_base_hotel_id', 'knowledge_base', 'hotels', ['hotel_id'], ['id'])
    op.create_foreign_key('fk_client_notes_hotel_id', 'client_notes', 'hotels', ['hotel_id'], ['id'])
    op.create_foreign_key('fk_operators_hotel_id', 'operators', 'hotels', ['hotel_id'], ['id'])

    # Indexes for query performance
    op.create_index('ix_clients_hotel_id', 'clients', ['hotel_id'])
    op.create_index('ix_conversations_hotel_id', 'conversations', ['hotel_id'])
    op.create_index('ix_knowledge_base_hotel_id', 'knowledge_base', ['hotel_id'])
    op.create_index('ix_client_notes_hotel_id', 'client_notes', ['hotel_id'])
    op.create_index('ix_operators_hotel_id', 'operators', ['hotel_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_operators_hotel_id', table_name='operators')
    op.drop_index('ix_client_notes_hotel_id', table_name='client_notes')
    op.drop_index('ix_knowledge_base_hotel_id', table_name='knowledge_base')
    op.drop_index('ix_conversations_hotel_id', table_name='conversations')
    op.drop_index('ix_clients_hotel_id', table_name='clients')

    # Drop foreign keys
    op.drop_constraint('fk_operators_hotel_id', 'operators', type_='foreignkey')
    op.drop_constraint('fk_client_notes_hotel_id', 'client_notes', type_='foreignkey')
    op.drop_constraint('fk_knowledge_base_hotel_id', 'knowledge_base', type_='foreignkey')
    op.drop_constraint('fk_conversations_hotel_id', 'conversations', type_='foreignkey')
    op.drop_constraint('fk_clients_hotel_id', 'clients', type_='foreignkey')

    # Make nullable again
    op.alter_column('operators', 'hotel_id', nullable=True)
    op.alter_column('client_notes', 'hotel_id', nullable=True)
    op.alter_column('knowledge_base', 'hotel_id', nullable=True)
    op.alter_column('conversations', 'hotel_id', nullable=True)
    op.alter_column('clients', 'hotel_id', nullable=True)
