"""Add multi-tenant tables (hotels, applications, platform_users) and hotel_id to existing tables

Revision ID: 007
Revises: 006
Create Date: 2026-04-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Новые таблицы ---

    op.create_table(
        'hotels',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('config', JSONB, nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('telegram_bot_token', sa.String(255), nullable=True),
        sa.Column('wappi_api_key', sa.String(255), nullable=True),
        sa.Column('wappi_profile_id', sa.String(255), nullable=True),
        sa.Column('pms_type', sa.String(50), nullable=True),
        sa.Column('pms_api_key', sa.String(255), nullable=True),
        sa.Column('pms_hotel_code', sa.String(100), nullable=True),
        sa.Column('ai_model', sa.String(255), server_default='anthropic/claude-3.5-haiku'),
        sa.Column('status', sa.Enum('active', 'paused', 'archived', name='hotelstatus'), server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_hotels_slug', 'hotels', ['slug'])

    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('status', sa.Enum('pending', 'configuring', 'active', 'rejected', name='applicationstatus'), server_default='pending'),
        sa.Column('hotel_name', sa.String(255), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('form_data', JSONB, nullable=True),
        sa.Column('generated_prompt', sa.Text(), nullable=True),
        sa.Column('hotel_id', sa.Integer(), sa.ForeignKey('hotels.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'platform_users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('superadmin', 'admin', name='platformrole'), server_default='superadmin'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- hotel_id в существующие таблицы (nullable для обратной совместимости) ---

    op.add_column('clients', sa.Column('hotel_id', sa.Integer(), nullable=True))
    op.add_column('conversations', sa.Column('hotel_id', sa.Integer(), nullable=True))
    op.add_column('knowledge_base', sa.Column('hotel_id', sa.Integer(), nullable=True))
    op.add_column('client_notes', sa.Column('hotel_id', sa.Integer(), nullable=True))
    op.add_column('operators', sa.Column('hotel_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('operators', 'hotel_id')
    op.drop_column('client_notes', 'hotel_id')
    op.drop_column('knowledge_base', 'hotel_id')
    op.drop_column('conversations', 'hotel_id')
    op.drop_column('clients', 'hotel_id')

    op.drop_table('platform_users')
    op.drop_table('applications')
    op.drop_index('ix_hotels_slug', table_name='hotels')
    op.drop_table('hotels')

    op.execute("DROP TYPE IF EXISTS hotelstatus")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
    op.execute("DROP TYPE IF EXISTS platformrole")
