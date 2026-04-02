import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import MessageCreate, MessageOut
from app.bot.channels.telegram import get_bot
from app.core.auth import get_current_operator
from app.db.database import get_session
from app.db.models.models import (
    ChannelType,
    Conversation,
    ConversationStatus,
    Message,
    MessageSender,
    Operator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["Messages"])


@router.get("/", response_model=list[MessageOut])
async def get_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Получить сообщения диалога с пагинацией."""
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Диалог не найден")

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=MessageOut, status_code=201)
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    session: AsyncSession = Depends(get_session),
    operator: Operator = Depends(get_current_operator),
):
    """Менеджер отправляет сообщение в диалог."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.client))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    # Переводим диалог в статус "оператор отвечает"
    if conversation.status != ConversationStatus.operator_active:
        conversation.status = ConversationStatus.operator_active
        conversation.assigned_operator_id = operator.id

    message = Message(
        conversation_id=conversation_id,
        sender=MessageSender.operator,
        text=data.text,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)

    # Отправляем сообщение клиенту в мессенджер
    client = conversation.client
    tg_bot = get_bot()

    if client.channel == ChannelType.whatsapp:
        try:
            from app.bot.channels.whatsapp import send_whatsapp_message
            success = await send_whatsapp_message(client.channel_user_id, data.text)
            if not success:
                logger.error(f"Не удалось отправить в WhatsApp: {client.channel_user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки в WhatsApp: {e}")
    elif client.channel == ChannelType.telegram:
        if tg_bot:
            try:
                await tg_bot.send_message(
                    chat_id=int(client.channel_user_id),
                    text=data.text,
                )
            except Exception as e:
                logger.error(f"Ошибка отправки в Telegram: {e}")

    # Уведомляем менеджеров в Telegram что диалог обработан из админки
    if tg_bot:
        try:
            from sqlalchemy import select as sa_select
            result = await session.execute(
                sa_select(Operator).where(
                    Operator.telegram_id.isnot(None),
                    Operator.is_active.is_(True),
                )
            )
            operators = result.scalars().all()
            client_name = client.name or "Гость"
            channel_name = "WhatsApp" if client.channel == ChannelType.whatsapp else "Telegram"
            for op in operators:
                if op.id == operator.id:
                    continue  # Не уведомляем того кто сам отправил
                try:
                    await tg_bot.send_message(
                        chat_id=op.telegram_id,
                        text=(
                            f"✅ {operator.name} ответил гостю {client_name} ({channel_name}) "
                            f"из админки (диалог #{conversation_id})"
                        ),
                    )
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Ошибка уведомления Telegram о действии из админки: {e}")

    return message
