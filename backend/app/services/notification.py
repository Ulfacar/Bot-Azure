# Сервис уведомлений менеджерам
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Operator, Conversation, Client, Message, ChannelType

logger = logging.getLogger(__name__)

# Хранилище состояний: operator_telegram_id -> conversation_id (какой менеджер отвечает на какой диалог)
operator_reply_state: dict[str, int] = {}

# Хранилище message_id уведомлений: conversation_id -> [(chat_id, message_id), ...]
_notification_messages: dict[int, list[tuple[str, int]]] = {}


def set_operator_replying(operator_telegram_id: str, conversation_id: int):
    """Установить состояние: менеджер отвечает на диалог."""
    operator_reply_state[operator_telegram_id] = conversation_id


def get_operator_replying(operator_telegram_id: str) -> int | None:
    """Получить ID диалога, на который отвечает менеджер."""
    return operator_reply_state.get(operator_telegram_id)


def clear_operator_replying(operator_telegram_id: str):
    """Очистить состояние ответа менеджера."""
    operator_reply_state.pop(operator_telegram_id, None)


async def get_operators_with_telegram(
    session: AsyncSession, hotel_id: int | None = None
) -> list[Operator]:
    """Получить активных менеджеров с telegram_id (для конкретного отеля или всех)."""
    query = select(Operator).where(
        Operator.is_active == True,
        Operator.telegram_id.isnot(None),
    )
    if hotel_id is not None:
        query = query.where(Operator.hotel_id == hotel_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_operator_by_telegram_id(session: AsyncSession, telegram_id: str) -> Operator | None:
    """Найти менеджера по telegram_id."""
    result = await session.execute(
        select(Operator).where(Operator.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def notify_operators_new_request(
    bot: Bot,
    session: AsyncSession,
    conversation: Conversation,
    client: Client,
    last_message: str,
    booking_data=None,
):
    """Отправить уведомление всем менеджерам о новом запросе.

    booking_data — BookingRequest из assistant.py (если это бронирование).
    """
    operators = await get_operators_with_telegram(session)

    if not operators:
        logger.warning("Нет менеджеров с telegram_id для уведомления")
        return

    # Формируем текст уведомления
    client_name = client.name or "Гость"
    client_username = f"@{client.username}" if client.username else ""

    # Определяем канал
    if client.channel == ChannelType.whatsapp:
        channel_icon = "📱"
        channel_name = "WhatsApp"
    else:
        channel_icon = "✈️"
        channel_name = "Telegram"

    # Если есть данные бронирования — расширенное уведомление
    if booking_data and booking_data.checkin:
        dates_str = ""
        if booking_data.checkin and booking_data.checkout:
            dates_str = (
                f"{booking_data.checkin.strftime('%d.%m.%Y')} — "
                f"{booking_data.checkout.strftime('%d.%m.%Y')} "
                f"({booking_data.nights} ноч.)"
            )

        guest_name = booking_data.guest_name or client_name
        phone = booking_data.phone or "не указан"
        adults = booking_data.adults or "не указано"

        text = (
            f"📋 <b>ЗАЯВКА НА БРОНЬ</b>\n\n"
            f"📅 <b>Даты:</b> {dates_str}\n"
            f"👥 <b>Гостей:</b> {adults}\n\n"
            f"👤 <b>Гость:</b> {guest_name}\n"
            f"📞 <b>Тел:</b> {phone}\n"
            f"{channel_icon} <b>Канал:</b> {channel_name} {client_username}\n\n"
            f"📍 Диалог #{conversation.id}"
        )
    else:
        text = (
            f"🔔 <b>Нужна помощь!</b>\n\n"
            f"👤 <b>Гость:</b> {client_name} {client_username}\n"
            f"{channel_icon} <b>Канал:</b> {channel_name}\n"
            f"💬 <b>Вопрос:</b>\n{last_message}\n\n"
            f"📍 Диалог #{conversation.id}"
        )

    # Кнопки
    buttons = [
        [
            InlineKeyboardButton(
                text="✍️ Ответить",
                callback_data=f"reply:{conversation.id}"
            ),
            InlineKeyboardButton(
                text="👀 История",
                callback_data=f"history:{conversation.id}"
            ),
        ]
    ]

    # Добавляем кнопку Exely если это заявка на бронь
    if booking_data and booking_data.checkin:
        buttons.append([
            InlineKeyboardButton(
                text="🏨 Открыть Exely",
                url="https://exely.io"
            ),
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем всем менеджерам и сохраняем message_id
    sent_messages: list[tuple[str, int]] = []
    for operator in operators:
        try:
            sent = await bot.send_message(
                chat_id=operator.telegram_id,
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            sent_messages.append((operator.telegram_id, sent.message_id))
            logger.info(f"Уведомление отправлено менеджеру {operator.name} (tg:{operator.telegram_id})")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления менеджеру {operator.name}: {e}")

    # Сохраняем message_id для возможности обновления из админки
    if sent_messages:
        _notification_messages[conversation.id] = sent_messages


async def mark_notification_handled(
    bot: Bot,
    conversation_id: int,
    handler_name: str = "Менеджер",
    source: str = "админки",
):
    """Обновить уведомления в Telegram — заменить кнопки на '✅ Обработано'."""
    messages = _notification_messages.pop(conversation_id, [])
    for chat_id, message_id in messages:
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=None,  # Убираем кнопки
            )
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"✅ Диалог #{conversation_id} обработан ({handler_name} из {source})",
            )
        except Exception as e:
            # Сообщение могло быть уже отредактировано или удалено
            logger.debug(f"Не удалось обновить уведомление: {e}")


async def send_history_to_operator(
    bot: Bot,
    session: AsyncSession,
    operator_telegram_id: str,
    conversation_id: int,
):
    """Отправить историю диалога менеджеру."""
    # Получаем сообщения
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(10)
    )
    messages = list(result.scalars().all())

    if not messages:
        await bot.send_message(
            chat_id=operator_telegram_id,
            text="История пуста",
        )
        return

    # Формируем текст истории
    lines = [f"📜 <b>История диалога #{conversation_id}</b>\n"]
    for msg in messages:
        sender_emoji = {
            "client": "👤",
            "bot": "🤖",
            "operator": "👨‍💼",
        }.get(msg.sender.value, "❓")

        # Обрезаем длинные сообщения
        text = msg.text[:200] + "..." if len(msg.text) > 200 else msg.text
        lines.append(f"{sender_emoji} {text}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✍️ Ответить",
                callback_data=f"reply:{conversation_id}"
            ),
        ]
    ])

    await bot.send_message(
        chat_id=operator_telegram_id,
        text="\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=keyboard,
    )
