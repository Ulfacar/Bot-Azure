import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import ClientNote


def normalize_phone(phone: str) -> str:
    """Нормализовать номер телефона — только цифры."""
    return re.sub(r"[^\d]", "", phone)


async def get_notes_for_phone(
    session: AsyncSession, phone: str
) -> list[ClientNote]:
    """Найти заметки менеджера по номеру телефона."""
    normalized = normalize_phone(phone)
    if not normalized:
        return []
    result = await session.execute(
        select(ClientNote)
        .where(ClientNote.phone == normalized)
        .order_by(ClientNote.created_at.desc())
    )
    return list(result.scalars().all())
