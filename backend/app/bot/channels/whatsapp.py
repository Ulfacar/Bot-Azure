"""
WhatsApp канал через Meta Cloud API или wappi.pro.
Обработка входящих сообщений и отправка ответов.
"""
import asyncio
import logging
import time
from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse

from app.bot.ai.assistant import (
    bot_completed,
    check_and_format_availability,
    clean_response,
    detect_category_from_text,
    extract_booking_data,
    extract_category,
    generate_response,
    needs_operator,
    format_knowledge_answer,
)
from app.db.database import async_session
from app.db.models.models import (
    ChannelType,
    ConversationCategory,
    ConversationStatus,
    MessageSender,
)
from app.services.conversation import (
    create_conversation,
    extract_and_save_phone,
    get_active_conversation,
    get_client_previous_messages,
    get_conversation_history,
    get_or_create_client,
    save_message,
)
from app.services.notification import notify_operators_new_request
from app.services.knowledge import search_knowledge_base
from app.services.meta_whatsapp import (
    send_whatsapp_message as send_meta_message,
    parse_webhook_message as parse_meta_webhook,
    is_whatsapp_configured as is_meta_configured,
)
from app.services.wappi_whatsapp import (
    send_wappi_message,
    parse_wappi_webhook,
    is_wappi_configured,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Debounce: собираем сообщения одного клиента, ждём паузу 1.5с ---
_message_buffers: dict[str, list[str]] = {}       # phone → [texts]
_buffer_locks: dict[str, asyncio.Lock] = {}        # phone → Lock
_buffer_tasks: dict[str, asyncio.Task] = {}        # phone → scheduled Task
_DEBOUNCE_DELAY = 1.5  # секунд


async def _debounced_handle(phone_number: str, profile_name: str):
    """Вызывается после паузы — обрабатывает все накопленные сообщения как одно."""
    await asyncio.sleep(_DEBOUNCE_DELAY)

    lock = _buffer_locks.get(phone_number)
    if not lock:
        return

    async with lock:
        messages = _message_buffers.pop(phone_number, [])
        _buffer_tasks.pop(phone_number, None)

    if not messages:
        return

    # Склеиваем все сообщения в одно
    combined_text = "\n".join(messages)
    logger.info(f"WhatsApp debounce: {phone_number} — {len(messages)} сообщ. объединено")

    await _handle_whatsapp_message_inner(
        phone_number=phone_number,
        message_text=combined_text,
        profile_name=profile_name,
    )


async def _enqueue_message(phone_number: str, message_text: str, profile_name: str):
    """Добавить сообщение в буфер и (пере)запустить таймер."""
    if phone_number not in _buffer_locks:
        _buffer_locks[phone_number] = asyncio.Lock()

    lock = _buffer_locks[phone_number]
    async with lock:
        _message_buffers.setdefault(phone_number, []).append(message_text)

        # Отменяем предыдущий таймер
        old_task = _buffer_tasks.get(phone_number)
        if old_task and not old_task.done():
            old_task.cancel()

        # Запускаем новый таймер
        _buffer_tasks[phone_number] = asyncio.create_task(
            _debounced_handle(phone_number, profile_name)
        )


def _use_wappi() -> bool:
    """Определить какой провайдер использовать. Wappi приоритетнее."""
    return is_wappi_configured()


async def send_whatsapp_message(to: str, text: str) -> bool:
    """Универсальная отправка — через wappi.pro или Meta."""
    if _use_wappi():
        return await send_wappi_message(to, text)
    return await send_meta_message(to, text)


def is_whatsapp_configured() -> bool:
    """Проверить настроен ли хоть один WhatsApp провайдер."""
    return is_wappi_configured() or is_meta_configured()


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(default=None, alias="hub.mode"),
    hub_verify_token: str = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str = Query(default=None, alias="hub.challenge"),
):
    """
    Верификация webhook от Meta (GET запрос).
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token and hub_challenge:
        logger.info("WhatsApp webhook верифицирован")
        return PlainTextResponse(hub_challenge)

    logger.warning("WhatsApp webhook верификация провалена")
    return PlainTextResponse("Forbidden", status_code=403)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Webhook для приёма сообщений от Meta WhatsApp Cloud API.
    """
    if not is_meta_configured():
        logger.warning("WhatsApp (Meta Cloud API) не настроен, игнорируем webhook")
        return PlainTextResponse("OK")

    try:
        data = await request.json()
    except Exception:
        return PlainTextResponse("OK")

    message_data = parse_meta_webhook(data)
    if not message_data:
        return PlainTextResponse("OK")

    try:
        await handle_whatsapp_message(
            phone_number=message_data["phone"],
            message_text=message_data["text"],
            profile_name=message_data["name"],
        )
    except Exception as e:
        logger.error(f"Ошибка обработки WhatsApp сообщения (Meta): {e}")

    return PlainTextResponse("OK")


@router.post("/webhook/wappi")
async def wappi_webhook(request: Request):
    """
    Webhook для приёма сообщений от wappi.pro.
    URL для настройки в wappi.pro: https://<domain>/api/webhook/wappi
    """
    if not is_wappi_configured():
        logger.warning("WhatsApp (wappi.pro) не настроен, игнорируем webhook")
        return PlainTextResponse("OK")

    try:
        data = await request.json()
    except Exception:
        return PlainTextResponse("OK")

    message_data = parse_wappi_webhook(data)
    if not message_data:
        return PlainTextResponse("OK")

    try:
        await handle_whatsapp_message(
            phone_number=message_data["phone"],
            message_text=message_data["text"],
            profile_name=message_data["name"],
        )
    except Exception as e:
        logger.error(f"Ошибка обработки WhatsApp сообщения (wappi.pro): {e}")

    return PlainTextResponse("OK")


_GREETING_WORDS = {
    "здравствуйте", "привет", "салам", "добрый день", "добрый вечер",
    "доброе утро", "хай", "hello", "hi", "hey", "ассалому алейкум",
    "салам алейкум", "ассаламу алейкум", "саламатсызбы", "саламатсызбы",
}


def _is_greeting(text: str) -> bool:
    """Проверить, является ли сообщение простым приветствием."""
    cleaned = text.strip().lower().rstrip("!.?,)")
    return cleaned in _GREETING_WORDS


async def handle_whatsapp_message(
    phone_number: str,
    message_text: str,
    profile_name: str,
):
    """
    Обработка входящего WhatsApp сообщения.
    Использует debounce — ждёт 1.5с перед обработкой, собирая все сообщения.
    """
    if not message_text.strip():
        return

    if len(message_text) > 4000:
        message_text = message_text[:4000]

    await _enqueue_message(phone_number, message_text, profile_name)


async def _handle_whatsapp_message_inner(
    phone_number: str,
    message_text: str,
    profile_name: str,
):
    """
    Реальная обработка WhatsApp сообщения (после debounce).
    """
    async with async_session() as session:
        # 1. Найти или создать клиента
        client = await get_or_create_client(
            session=session,
            channel=ChannelType.whatsapp,
            channel_user_id=phone_number,
            name=profile_name or phone_number,
            username=None,
        )

        # 2. Найти активный диалог или создать новый
        conversation = await get_active_conversation(session, client.id)
        is_new_conversation = conversation is None
        if not conversation:
            conversation = await create_conversation(session, client.id)

        # 2.1. Приветствие для нового диалога (только если просто здороваются)
        if is_new_conversation and _is_greeting(message_text):
            greeting = (
                "Здравствуйте! Благодарим за обращение в Тон Азур 😊\n"
                "Чем могу помочь?"
            )
            await send_whatsapp_message(phone_number, greeting)
            await save_message(
                session, conversation.id, MessageSender.bot, greeting
            )
            await save_message(
                session, conversation.id, MessageSender.client, message_text
            )
            await session.commit()
            return  # Не вызываем AI — приветствие уже отправлено

        # 3. Сохранить сообщение клиента
        await save_message(
            session, conversation.id, MessageSender.client, message_text
        )

        # 3.1. Извлечь и сохранить телефон, если есть
        await extract_and_save_phone(session, client.id, message_text)

        # 4. Если диалог ведёт оператор или ждёт менеджера — пересылаем ему сообщение
        if conversation.status in (ConversationStatus.operator_active, ConversationStatus.needs_operator):
            if conversation.assigned_operator_id:
                from app.db.models.models import Operator
                from app.bot.channels.telegram import get_bot
                from sqlalchemy import select as sa_select

                op_result = await session.execute(
                    sa_select(Operator).where(Operator.id == conversation.assigned_operator_id)
                )
                assigned_operator = op_result.scalar_one_or_none()
                tg_bot = get_bot()
                if assigned_operator and assigned_operator.telegram_id and tg_bot:
                    try:
                        await tg_bot.send_message(
                            chat_id=assigned_operator.telegram_id,
                            text=f"💬 Новое сообщение от гостя в WhatsApp (диалог #{conversation.id}):\n\n{message_text}",
                        )
                    except Exception as e:
                        logger.error(f"Ошибка уведомления менеджера о WhatsApp сообщении: {e}")
            await session.commit()
            return

        # 4.5. Обновляем категорию по тексту клиента (если ещё general)
        if conversation.category == ConversationCategory.general:
            text_category = detect_category_from_text(message_text)
            if text_category:
                try:
                    conversation.category = ConversationCategory(text_category)
                except ValueError:
                    pass

        # 5. Ищем ответ в базе знаний
        knowledge_entry = await search_knowledge_base(session, message_text)

        if knowledge_entry:
            # Нашли ответ в базе знаний
            response_text = format_knowledge_answer(knowledge_entry.answer)
            logger.info(f"WhatsApp: ответ из базы знаний (id={knowledge_entry.id})")
        else:
            # Спрашиваем AI
            history = await get_conversation_history(session, conversation.id)
            previous_context = await get_client_previous_messages(
                session, client.id, conversation.id
            )

            # Подсказка из базы знаний (для первых 2 сообщений)
            knowledge_hint = None
            client_msg_count = sum(1 for m in history if m.sender == MessageSender.client)
            if client_msg_count <= 2:
                kb_result = await search_knowledge_base(session, message_text)
                if kb_result:
                    knowledge_hint = f"Вопрос: {kb_result.question}\nОтвет: {kb_result.answer}"

            # Проверка доступности номеров через Exely PMS
            all_messages = history + ([type('M', (), {'text': message_text, 'sender': MessageSender.client})()] if not any(m.text == message_text for m in history) else [])
            availability_text = await check_and_format_availability(all_messages)
            if availability_text:
                knowledge_hint = (knowledge_hint or "") + f"\n\n=== ДАННЫЕ ИЗ СИСТЕМЫ БРОНИРОВАНИЯ ===\n{availability_text}\n=== ИСПОЛЬЗУЙ ЭТИ ДАННЫЕ В ОТВЕТЕ ==="

            response_text = await generate_response(history, previous_context, knowledge_hint)

            # Извлекаем категорию из ответа AI или из текста клиента
            category = extract_category(response_text)
            if not category:
                category = detect_category_from_text(message_text)
            if category and conversation.category == ConversationCategory.general:
                try:
                    conversation.category = ConversationCategory(category)
                except ValueError:
                    pass

            # Проверяем нужен ли менеджер
            need_operator = needs_operator(response_text)
            if need_operator:
                conversation.status = ConversationStatus.needs_operator
            elif bot_completed(response_text):
                conversation.status = ConversationStatus.bot_completed

            response_text = clean_response(response_text)

            # Уведомляем менеджеров если нужно
            if need_operator:
                # Извлекаем данные бронирования для уведомления
                all_msgs = await get_conversation_history(session, conversation.id, limit=20)
                booking_data = extract_booking_data(all_msgs)

                await session.commit()
                from app.bot.channels.telegram import get_bot

                bot = get_bot()
                if bot:
                    await notify_operators_new_request(
                        bot=bot,
                        session=session,
                        conversation=conversation,
                        client=client,
                        last_message=message_text,
                        booking_data=booking_data,
                    )

        # 6. Сохранить ответ бота
        await save_message(
            session, conversation.id, MessageSender.bot, response_text
        )
        await session.commit()

        # 7. Отправить ответ клиенту через WhatsApp
        await send_whatsapp_message(phone_number, response_text)


async def send_operator_reply_to_whatsapp(phone_number: str, message: str) -> bool:
    """
    Отправить ответ оператора клиенту в WhatsApp.
    Используется из Telegram при ответе менеджера.
    """
    return await send_whatsapp_message(phone_number, message)
