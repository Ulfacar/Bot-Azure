from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import NoteCreate, NoteOut, NoteUpdate
from app.core.auth import get_current_operator
from app.db.database import get_session
from app.db.models.models import Client, ClientNote, Operator
from app.services.notes import normalize_phone

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("/", response_model=list[NoteOut])
async def list_notes(
    phone: str = Query(..., description="Номер телефона"),
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Получить заметки по номеру телефона."""
    normalized = normalize_phone(phone)
    result = await session.execute(
        select(ClientNote)
        .where(ClientNote.phone == normalized)
        .order_by(ClientNote.created_at.desc())
    )
    return result.scalars().all()


@router.get("/by-client/{client_id}", response_model=list[NoteOut])
async def list_notes_by_client(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Получить заметки по client_id (ищет phone клиента или channel_user_id для WhatsApp)."""
    result = await session.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Для WhatsApp channel_user_id = номер телефона
    phone = client.phone or (
        client.channel_user_id if client.channel.value == "whatsapp" else None
    )
    if not phone:
        return []

    normalized = normalize_phone(phone)
    result = await session.execute(
        select(ClientNote)
        .where(ClientNote.phone == normalized)
        .order_by(ClientNote.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=NoteOut, status_code=201)
async def create_note(
    data: NoteCreate,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Создать заметку о клиенте."""
    note = ClientNote(
        phone=normalize_phone(data.phone),
        text=data.text,
        added_by_id=operator.id,
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


@router.put("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: int,
    data: NoteUpdate,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Редактировать заметку."""
    result = await session.execute(
        select(ClientNote).where(ClientNote.id == note_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    note.text = data.text
    await session.commit()
    await session.refresh(note)
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Удалить заметку."""
    result = await session.execute(
        select(ClientNote).where(ClientNote.id == note_id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    await session.delete(note)
    await session.commit()
