import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import (
    ChannelType,
    Client,
    Conversation,
    ConversationStatus,
    Message,
    MessageSender,
)

# Паттерн для номеров телефонов Кыргызстана и международных
_PHONE_RE = re.compile(
    r"(?:\+?996|0)\s*\d{3}\s*\d{3}\s*\d{3}"  # KG: +996XXX или 0XXX
    r"|"
    r"\+?\d[\d\s\-]{8,14}\d"  # Международный формат
)


async def get_or_create_client(
    session: AsyncSession,
    channel: ChannelType,
    channel_user_id: str,
    name: str | None = None,
    username: str | None = None,
) -> Client:
    """Найти клиента по мессенджеру или создать нового."""
    result = await session.execute(
        select(Client).where(
            Client.channel == channel,
            Client.channel_user_id == channel_user_id,
        )
    )
    client = result.scalar_one_or_none()

    if client:
        # Обновляем имя/username если изменились
        if name and client.name != name:
            client.name = name
        if username and client.username != username:
            client.username = username
        await session.commit()
        return client

    client = Client(
        channel=channel,
        channel_user_id=channel_user_id,
        name=name,
        username=username,
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def get_active_conversation(
    session: AsyncSession, client_id: int, reopen_hours: int = 24
) -> Conversation | None:
    """Найти активный (незакрытый) диалог клиента.
    bot_completed считается завершённым.
    closed в окне reopen_hours — переоткрывается (гость вернулся)."""
    # 1. Ищем активный диалог
    result = await session.execute(
        select(Conversation)
        .where(
            Conversation.client_id == client_id,
            Conversation.status.in_([
                ConversationStatus.in_progress,
                ConversationStatus.needs_operator,
                ConversationStatus.operator_active,
            ]),
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    active = result.scalar_one_or_none()
    if active:
        return active

    # 2. Ищем недавно закрытый диалог (в окне reopen_hours)
    cutoff = datetime.utcnow() - timedelta(hours=reopen_hours)
    result = await session.execute(
        select(Conversation)
        .where(
            Conversation.client_id == client_id,
            Conversation.status == ConversationStatus.closed,
            Conversation.updated_at >= cutoff,
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    closed_conv = result.scalar_one_or_none()
    if closed_conv:
        closed_conv.status = ConversationStatus.in_progress
        await session.commit()
        return closed_conv

    return None


async def create_conversation(
    session: AsyncSession, client_id: int
) -> Conversation:
    """Создать новый диалог."""
    conversation = Conversation(client_id=client_id)
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def save_message(
    session: AsyncSession,
    conversation_id: int,
    sender: MessageSender,
    text: str,
) -> Message:
    """Сохранить сообщение в БД."""
    message = Message(
        conversation_id=conversation_id,
        sender=sender,
        text=text,
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def extract_and_save_phone(
    session: AsyncSession, client_id: int, text: str
) -> str | None:
    """Извлечь номер телефона из сообщения клиента и сохранить в БД.

    Возвращает найденный номер или None.
    """
    match = _PHONE_RE.search(text)
    if not match:
        return None

    phone = re.sub(r"[\s\-]", "", match.group())  # Убираем пробелы и дефисы

    result = await session.execute(
        select(Client).where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if client and not client.phone:
        client.phone = phone
        await session.commit()

    return phone


async def get_conversation_history(
    session: AsyncSession, conversation_id: int, limit: int = 10
) -> list[Message]:
    """Получить последние N сообщений диалога."""
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()  # Хронологический порядок
    return messages


async def get_client_previous_messages(
    session: AsyncSession,
    client_id: int,
    current_conversation_id: int,
    limit: int = 10,
) -> list[Message]:
    """Получить последние сообщения клиента из предыдущих диалогов.

    Используется для кросс-диалоговой памяти — бот помнит контекст
    из прошлых разговоров с тем же клиентом.
    """
    # Находим предыдущие диалоги этого клиента (кроме текущего)
    conv_result = await session.execute(
        select(Conversation.id)
        .where(
            Conversation.client_id == client_id,
            Conversation.id != current_conversation_id,
        )
        .order_by(Conversation.updated_at.desc())
        .limit(3)  # Берём максимум 3 последних диалога
    )
    prev_conv_ids = [row[0] for row in conv_result.all()]

    if not prev_conv_ids:
        return []

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id.in_(prev_conv_ids))
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return messages


async def close_stale_conversations(session: AsyncSession, timeout_hours: int = 1) -> int:
    """Закрыть неактивные диалоги.
    - in_progress без активности > timeout_hours → closed
    - bot_completed без активности > timeout_hours → closed
    - needs_operator без активности > 4 часов → closed
    НЕ трогает operator_active (менеджер работает).
    Возвращает количество закрытых диалогов."""
    cutoff = datetime.utcnow() - timedelta(hours=timeout_hours)
    cutoff_long = datetime.utcnow() - timedelta(hours=4)

    # Закрываем in_progress и bot_completed
    result1 = await session.execute(
        update(Conversation)
        .where(
            Conversation.status.in_([
                ConversationStatus.in_progress,
                ConversationStatus.bot_completed,
            ]),
            Conversation.updated_at < cutoff,
        )
        .values(status=ConversationStatus.closed)
    )

    # Закрываем зависшие needs_operator (4 часа без ответа менеджера)
    result2 = await session.execute(
        update(Conversation)
        .where(
            Conversation.status == ConversationStatus.needs_operator,
            Conversation.updated_at < cutoff_long,
        )
        .values(status=ConversationStatus.closed)
    )

    await session.commit()
    return result1.rowcount + result2.rowcount
