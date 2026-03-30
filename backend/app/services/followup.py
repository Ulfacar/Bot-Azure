"""Сервис дожима — напоминания клиентам которые замолчали."""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import (
    Conversation, ConversationStatus, Message, MessageSender, Client, ChannelType,
)

logger = logging.getLogger(__name__)

# Тексты дожима
FOLLOWUP_1 = "Вы ещё с нами? 😊 Могу помочь с бронированием или ответить на вопросы!"
FOLLOWUP_2 = "Если будут вопросы — пишите, мы всегда на связи! 🏨"

# Маркер чтобы не слать дожим бесконечно
FOLLOWUP_MARKER = "[followup]"


async def send_followups(session: AsyncSession) -> int:
    """Найти диалоги где клиент замолчал и отправить напоминание.

    Логика:
    - Диалог in_progress
    - Последнее сообщение от бота (клиент не ответил)
    - Прошло 10+ минут — первый дожим
    - Прошло 25+ минут — второй дожим
    - Больше не трогаем

    Возвращает количество отправленных напоминаний.
    """
    from app.bot.channels.telegram import get_bot
    from app.bot.channels.whatsapp import send_whatsapp_message
    from app.services.conversation import save_message

    sent = 0

    # Берём активные диалоги
    result = await session.execute(
        select(Conversation)
        .where(Conversation.status == ConversationStatus.in_progress)
    )
    conversations = list(result.scalars().all())

    for conv in conversations:
        # Получаем последние сообщения
        msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        recent_msgs = list(msg_result.scalars().all())

        if not recent_msgs:
            continue

        last_msg = recent_msgs[0]

        # Если последнее сообщение от клиента — не трогаем (бот ещё не ответил или уже ответит)
        if last_msg.sender == MessageSender.client:
            continue

        # Если последнее от оператора — не трогаем
        if last_msg.sender == MessageSender.operator:
            continue

        # Последнее от бота — проверяем сколько прошло
        now = datetime.utcnow()
        minutes_since = (now - last_msg.created_at).total_seconds() / 60

        # Считаем сколько дожимов уже было
        followup_count = sum(
            1 for m in recent_msgs
            if m.sender == MessageSender.bot and FOLLOWUP_MARKER in (m.text or "")
        )

        # Определяем какой дожим нужен
        if followup_count == 0 and minutes_since >= 10:
            followup_text = FOLLOWUP_1
        elif followup_count == 1 and minutes_since >= 15:
            followup_text = FOLLOWUP_2
        else:
            continue  # Либо рано, либо уже 2 дожима

        # Получаем клиента
        client_result = await session.execute(
            select(Client).where(Client.id == conv.client_id)
        )
        client = client_result.scalar_one_or_none()
        if not client:
            continue

        # Сохраняем с маркером (маркер не видно клиенту — обрезаем при отправке)
        stored_text = f"{followup_text} {FOLLOWUP_MARKER}"
        await save_message(session, conv.id, MessageSender.bot, stored_text)

        # Отправляем клиенту
        try:
            if client.channel == ChannelType.telegram:
                bot = get_bot()
                if bot:
                    await bot.send_message(
                        chat_id=int(client.channel_user_id),
                        text=followup_text,
                    )
            elif client.channel == ChannelType.whatsapp:
                await send_whatsapp_message(client.channel_user_id, followup_text)

            sent += 1
            logger.info(
                f"Дожим #{followup_count + 1} отправлен: диалог #{conv.id}, "
                f"клиент {client.name} ({client.channel.value})"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки дожима (диалог #{conv.id}): {e}")

    return sent
