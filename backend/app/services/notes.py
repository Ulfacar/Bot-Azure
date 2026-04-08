import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import ClientNote


def normalize_phone(phone: str) -> str:
    """Нормализовать номер телефона — только цифры."""
    return re.sub(r"[^\d]", "", phone)


async def get_notes_for_phone(
    session: AsyncSession, phone: str, hotel_id: int | None = None
) -> list[ClientNote]:
    """Найти заметки менеджера по номеру телефона."""
    normalized = normalize_phone(phone)
    if not normalized:
        return []
    query = select(ClientNote).where(ClientNote.phone == normalized)
    if hotel_id is not None:
        query = query.where(ClientNote.hotel_id == hotel_id)
    query = query.order_by(ClientNote.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())
