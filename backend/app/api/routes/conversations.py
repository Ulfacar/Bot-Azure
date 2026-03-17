from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, case, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import ConversationOut, ConversationUpdate
from app.core.auth import get_current_operator
from app.db.database import get_session
from app.db.models.models import Client, Conversation, ConversationStatus, Message, MessageSender, Operator

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("/", response_model=list[ConversationOut])
async def list_conversations(
    status_filter: Optional[ConversationStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Список диалогов с фильтрацией по статусу и поиском по имени клиента."""
    query = (
        select(Conversation)
        .join(Client)
        .options(selectinload(Conversation.client))
        .order_by(Conversation.updated_at.desc())
    )

    if status_filter:
        query = query.where(Conversation.status == status_filter)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (Client.name.ilike(pattern)) | (Client.username.ilike(pattern))
        )

    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    return result.scalars().all()


@router.get("/stats", response_model=dict)
async def get_stats(
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Статистика диалогов за сегодня и всего."""
    # Сегодня по UTC+6 (Кыргызстан), но без таймзоны для совместимости с БД
    now = datetime.utcnow() + timedelta(hours=6)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Всего по статусам
    result = await session.execute(
        select(Conversation.status, func.count())
        .group_by(Conversation.status)
    )
    total_by_status = {row[0]: row[1] for row in result.all()}

    # Сегодня по статусам
    result = await session.execute(
        select(Conversation.status, func.count())
        .where(Conversation.created_at >= today_start)
        .group_by(Conversation.status)
    )
    today_by_status = {row[0]: row[1] for row in result.all()}

    total_all = sum(total_by_status.values())
    today_all = sum(today_by_status.values())

    return {
        "today": {
            "total": today_all,
            "bot_completed": today_by_status.get(ConversationStatus.bot_completed, 0),
            "needs_operator": today_by_status.get(ConversationStatus.needs_operator, 0),
            "operator_active": today_by_status.get(ConversationStatus.operator_active, 0),
            "in_progress": today_by_status.get(ConversationStatus.in_progress, 0),
            "closed": today_by_status.get(ConversationStatus.closed, 0),
        },
        "total": {
            "total": total_all,
            "bot_completed": total_by_status.get(ConversationStatus.bot_completed, 0),
            "needs_operator": total_by_status.get(ConversationStatus.needs_operator, 0),
            "operator_active": total_by_status.get(ConversationStatus.operator_active, 0),
            "in_progress": total_by_status.get(ConversationStatus.in_progress, 0),
            "closed": total_by_status.get(ConversationStatus.closed, 0),
        },
    }


@router.get("/stats/efficiency", response_model=dict)
async def get_efficiency(
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Расширенная статистика эффективности бота."""
    now = datetime.utcnow() + timedelta(hours=6)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Общее количество завершённых диалогов (не in_progress)
    finished_statuses = [
        ConversationStatus.bot_completed,
        ConversationStatus.closed,
        ConversationStatus.needs_operator,
        ConversationStatus.operator_active,
    ]

    result = await session.execute(
        select(
            func.count(Conversation.id).label("total_finished"),
            func.count(case(
                (Conversation.status == ConversationStatus.bot_completed, 1),
            )).label("bot_solved"),
            func.count(case(
                (Conversation.status.in_([
                    ConversationStatus.needs_operator,
                    ConversationStatus.operator_active,
                ]), 1),
            )).label("escalated"),
        )
        .where(Conversation.status.in_(finished_statuses))
    )
    row = result.one()
    total_finished = row.total_finished or 0
    bot_solved = row.bot_solved or 0
    escalated = row.escalated or 0

    # Среднее кол-во сообщений бота на диалог
    result = await session.execute(
        select(func.avg(func.count(Message.id)))
        .where(Message.sender == MessageSender.bot)
        .group_by(Message.conversation_id)
    )
    avg_bot_messages = result.scalar() or 0

    # Уникальные клиенты
    result = await session.execute(
        select(func.count(distinct(Conversation.client_id)))
    )
    unique_clients = result.scalar() or 0

    # Сегодня
    result = await session.execute(
        select(
            func.count(Conversation.id).label("today_total"),
            func.count(case(
                (Conversation.status == ConversationStatus.bot_completed, 1),
            )).label("today_bot_solved"),
        )
        .where(Conversation.created_at >= today_start)
        .where(Conversation.status.in_(finished_statuses))
    )
    today_row = result.one()

    return {
        "total_finished": total_finished,
        "bot_solved": bot_solved,
        "escalated": escalated,
        "efficiency_percent": round(bot_solved / total_finished * 100) if total_finished > 0 else 0,
        "avg_bot_messages": round(float(avg_bot_messages), 1),
        "unique_clients": unique_clients,
        "today": {
            "total_finished": today_row.today_total or 0,
            "bot_solved": today_row.today_bot_solved or 0,
            "efficiency_percent": round(
                (today_row.today_bot_solved or 0) / (today_row.today_total or 1) * 100
            ) if (today_row.today_total or 0) > 0 else 0,
        },
    }


@router.get("/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: int,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Получить один диалог по ID."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.client))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Обновить статус, категорию или назначить оператора."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.client))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    if data.status is not None:
        conversation.status = data.status
    if data.category is not None:
        conversation.category = data.category
    if data.assigned_operator_id is not None:
        conversation.assigned_operator_id = data.assigned_operator_id

    await session.commit()
    await session.refresh(conversation)
    return conversation
