import logging

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.bot.ai.assistant import (
    bot_completed,
    clean_response,
    detect_category_from_text,
    ensure_room_variants,
    extract_category,
    fix_prices_in_response,
    generate_response,
    needs_operator,
    check_and_format_availability,
    extract_booking_data,
)
from app.core.config import settings
from app.db.database import async_session
from app.db.models.models import (
    ChannelType,
    ConversationCategory,
    ConversationStatus,
    MessageSender,
    Conversation,
    Client,
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
from app.services.notification import (
    notify_operators_new_request,
    send_history_to_operator,
    get_operator_by_telegram_id,
    set_operator_replying,
    get_operator_replying,
    clear_operator_replying,
)
from app.services.knowledge import (
    search_knowledge_base,
    add_to_knowledge_base,
    get_last_qa_pair,
    should_auto_save_to_knowledge,
)
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = Router()
bot: Bot | None = None
dp: Dispatcher | None = None

# === Шаблоны быстрых ответов менеджера ===
MANAGER_TEMPLATES = {
    "tpl_payment": (
        "💰 Реквизиты для оплаты:\n\n"
        "[РЕКВИЗИТЫ]\n\n"
        "После оплаты, пожалуйста, пришлите скриншот или чек — "
        "и мы подтвердим бронирование 😊"
    ),
    "tpl_confirmed": (
        "Отличная новость — ваша бронь подтверждена! ✅\n\n"
        "Мы будем рады видеть вас в Тон Азур. "
        "Если появятся вопросы до заезда — пишите, всегда на связи 😊"
    ),
    "tpl_no_rooms": (
        "К сожалению, на выбранные даты свободных номеров нет 😔\n\n"
        "Могу предложить посмотреть ближайшие доступные даты — "
        "хотите, подберём альтернативный вариант?"
    ),
    "tpl_directions": (
        "🚗 Как добраться до Тон Азур:\n\n"
        "Мы находимся в 278 км от Бишкека — это примерно 4–4,5 часа на авто.\n\n"
        "🛫 Трансфер от аэропорта Манас — 10 000 сом.\n"
        "Аэропорт Тамчы — 146 км, трансфер индивидуально.\n"
        "Летом — бесплатный трансфер до пляжей.\n\n"
        "Если нужен трансфер — напишите, организуем! 😊"
    ),
    "tpl_cancellation": (
        "📋 Условия отмены бронирования:\n\n"
        "• Более чем за 48 часов до заезда — отмена бесплатна.\n"
        "• Менее чем за 48 часов — предоплата не возвращается.\n\n"
        "Если есть вопросы — с удовольствием подскажу 😊"
    ),
}


def _build_operator_reply_keyboard(conversation_id: int) -> InlineKeyboardMarkup:
    """Клавиатура с шаблонами и кнопкой завершения для менеджера."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Реквизиты", callback_data=f"tpl_payment:{conversation_id}"),
            InlineKeyboardButton(text="✅ Подтверждена", callback_data=f"tpl_confirmed:{conversation_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Нет мест", callback_data=f"tpl_no_rooms:{conversation_id}"),
            InlineKeyboardButton(text="🚗 Добраться", callback_data=f"tpl_directions:{conversation_id}"),
        ],
        [
            InlineKeyboardButton(text="📋 Условия отмены", callback_data=f"tpl_cancellation:{conversation_id}"),
        ],
        [
            InlineKeyboardButton(text="✅ Завершить диалог", callback_data=f"finish:{conversation_id}"),
        ],
    ])


@router.message(CommandStart())
async def handle_start(message: types.Message):
    """Обработка команды /start."""
    async with async_session() as session:
        # Проверяем, может это менеджер
        operator = await get_operator_by_telegram_id(session, str(message.from_user.id))
        if operator:
            await message.answer(
                f"👋 Привет, {operator.name}!\n\n"
                "Вы подключены как менеджер отеля.\n"
                "Когда гостю понадобится помощь — я пришлю уведомление."
            )
            return

        # Обычный клиент
        await get_or_create_client(
            session=session,
            channel=ChannelType.telegram,
            channel_user_id=str(message.from_user.id),
            name=message.from_user.full_name,
            username=message.from_user.username,
        )

    await message.answer(
        "Здравствуйте! Благодарим за обращение в Тон Азур 😊\n"
        "Чем могу помочь?"
    )


@router.callback_query(F.data.startswith("reply:"))
async def handle_reply_callback(callback: types.CallbackQuery):
    """Обработка нажатия кнопки 'Ответить'."""
    conversation_id = int(callback.data.split(":")[1])
    operator_telegram_id = str(callback.from_user.id)

    async with async_session() as session:
        operator = await get_operator_by_telegram_id(session, operator_telegram_id)
        if not operator:
            await callback.answer("Вы не зарегистрированы как менеджер", show_alert=True)
            return

        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            await callback.answer("Диалог не найден", show_alert=True)
            return

        conversation.status = ConversationStatus.operator_active
        conversation.assigned_operator_id = operator.id
        await session.commit()

    set_operator_replying(operator_telegram_id, conversation_id)

    await callback.answer()
    await callback.message.answer(
        f"✍️ Вы взяли диалог #{conversation_id}.\n\n"
        "Напишите ответ или выберите шаблон:",
        reply_markup=_build_operator_reply_keyboard(conversation_id),
    )


@router.callback_query(F.data.startswith("history:"))
async def handle_history_callback(callback: types.CallbackQuery):
    """Обработка нажатия кнопки 'История'."""
    conversation_id = int(callback.data.split(":")[1])
    operator_telegram_id = str(callback.from_user.id)

    async with async_session() as session:
        operator = await get_operator_by_telegram_id(session, operator_telegram_id)
        if not operator:
            await callback.answer("Вы не зарегистрированы как менеджер", show_alert=True)
            return

        await send_history_to_operator(
            bot=callback.bot,
            session=session,
            operator_telegram_id=operator_telegram_id,
            conversation_id=conversation_id,
        )

    await callback.answer()


@router.callback_query(F.data.startswith("save_kb:"))
async def handle_save_knowledge_callback(callback: types.CallbackQuery):
    """Обработка нажатия кнопки 'Запомнить'."""
    conversation_id = int(callback.data.split(":")[1])
    operator_telegram_id = str(callback.from_user.id)

    async with async_session() as session:
        operator = await get_operator_by_telegram_id(session, operator_telegram_id)
        if not operator:
            await callback.answer("Ошибка", show_alert=True)
            return

        # Получаем последнюю пару вопрос-ответ
        qa_pair = await get_last_qa_pair(session, conversation_id)
        if not qa_pair:
            await callback.answer("Не удалось найти вопрос-ответ", show_alert=True)
            return

        question, answer = qa_pair

        # Сохраняем в базу знаний
        await add_to_knowledge_base(
            session=session,
            question=question,
            answer=answer,
            operator_id=operator.id,
            conversation_id=conversation_id,
        )

    await callback.answer("✅ Сохранено в базу знаний!")
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Добавлено в базу знаний!</b>\n"
        "Теперь бот сможет отвечать на похожие вопросы сам.",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("skip_kb:"))
async def handle_skip_knowledge_callback(callback: types.CallbackQuery):
    """Обработка нажатия кнопки 'Не сохранять'."""
    await callback.answer()
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ Не сохранено.",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("tpl_"))
async def handle_template_callback(callback: types.CallbackQuery):
    """Обработка нажатия шаблона быстрого ответа."""
    # Парсим: "tpl_payment:28" → key="tpl_payment", conv_id=28
    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Ошибка", show_alert=True)
        return

    template_key = parts[0]
    conversation_id = int(parts[1])
    operator_telegram_id = str(callback.from_user.id)

    template_text = MANAGER_TEMPLATES.get(template_key)
    if not template_text:
        await callback.answer("Шаблон не найден", show_alert=True)
        return

    async with async_session() as session:
        operator = await get_operator_by_telegram_id(session, operator_telegram_id)
        if not operator:
            await callback.answer("Вы не зарегистрированы как менеджер", show_alert=True)
            return

        # Убедимся что менеджер привязан к диалогу
        current_conv = get_operator_replying(operator_telegram_id)
        if current_conv != conversation_id:
            set_operator_replying(operator_telegram_id, conversation_id)
            result = await session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if conv:
                conv.status = ConversationStatus.operator_active
                conv.assigned_operator_id = operator.id
                await session.commit()

        # Получаем диалог и клиента
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            await callback.answer("Диалог не найден", show_alert=True)
            return

        result = await session.execute(
            select(Client).where(Client.id == conversation.client_id)
        )
        client = result.scalar_one_or_none()
        if not client:
            await callback.answer("Клиент не найден", show_alert=True)
            return

        # Сохраняем и отправляем
        await save_message(session, conversation_id, MessageSender.operator, template_text)
        await session.commit()

        try:
            if client.channel == ChannelType.whatsapp:
                from app.bot.channels.whatsapp import send_whatsapp_message
                success = await send_whatsapp_message(client.channel_user_id, template_text)
                if not success:
                    raise Exception("Не удалось отправить в WhatsApp")
            else:
                await callback.bot.send_message(
                    chat_id=client.channel_user_id,
                    text=template_text,
                )

            channel_name = "WhatsApp" if client.channel == ChannelType.whatsapp else "Telegram"
            await callback.answer("✅ Отправлено!")
            await callback.message.answer(
                f"✅ Шаблон отправлен гостю ({channel_name})!\n\n"
                "Можете написать ещё или выбрать другой шаблон:",
                reply_markup=_build_operator_reply_keyboard(conversation_id),
            )
        except Exception as e:
            logger.error(f"Ошибка отправки шаблона клиенту: {e}")
            await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("finish:"))
async def handle_finish_callback(callback: types.CallbackQuery):
    """Обработка нажатия кнопки 'Завершить диалог'."""
    conversation_id = int(callback.data.split(":")[1])
    operator_telegram_id = str(callback.from_user.id)

    async with async_session() as session:
        operator = await get_operator_by_telegram_id(session, operator_telegram_id)
        if not operator:
            await callback.answer("Ошибка", show_alert=True)
            return

        # Закрываем диалог
        result = await session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.status = ConversationStatus.closed
            await session.commit()

        # Очищаем состояние
        clear_operator_replying(operator_telegram_id)

        # Проверяем нужно ли автосохранить в базу знаний
        qa_pair = await get_last_qa_pair(session, conversation_id)

        if qa_pair:
            question, answer = qa_pair

            # Умная фильтрация — сохраняем только общие вопросы
            if should_auto_save_to_knowledge(question):
                await add_to_knowledge_base(
                    session=session,
                    question=question,
                    answer=answer,
                    operator_id=operator.id,
                    conversation_id=conversation_id,
                )
                await callback.answer()
                await callback.message.edit_text(
                    "✅ Диалог завершён.\n\n"
                    "🧠 Бот запомнил этот ответ и в следующий раз ответит сам!"
                )
            else:
                await callback.answer()
                await callback.message.edit_text(
                    "✅ Диалог завершён. Жду новых уведомлений."
                )
        else:
            await callback.answer()
            await callback.message.edit_text(
                "✅ Диалог завершён. Жду новых уведомлений."
            )


@router.message()
async def handle_message(message: types.Message):
    """Обработка любого текстового сообщения."""
    if not message.text:
        await message.answer("Пока я понимаю только текстовые сообщения.")
        return

    if len(message.text) > 4000:
        await message.answer("Сообщение слишком длинное. Пожалуйста, сократите до 4000 символов.")
        return

    user_telegram_id = str(message.from_user.id)

    async with async_session() as session:
        operator = await get_operator_by_telegram_id(session, user_telegram_id)

        if operator:
            await handle_operator_message(message, session, operator, user_telegram_id)
            return

        await handle_client_message(message, session)


async def handle_operator_message(message: types.Message, session, operator, operator_telegram_id: str):
    """Обработка сообщения от менеджера."""
    # Команда завершения
    if message.text in ("/done", "/cancel"):
        conversation_id = get_operator_replying(operator_telegram_id)
        clear_operator_replying(operator_telegram_id)

        if conversation_id:
            # Закрываем диалог чтобы клиент мог начать новый
            result = await session.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.status = ConversationStatus.closed
                await session.commit()

            # Проверяем нужно ли автосохранить в базу знаний
            qa_pair = await get_last_qa_pair(session, conversation_id)

            if qa_pair:
                question, answer = qa_pair

                # Умная фильтрация — сохраняем только общие вопросы
                if should_auto_save_to_knowledge(question):
                    await add_to_knowledge_base(
                        session=session,
                        question=question,
                        answer=answer,
                        operator_id=operator.id,
                        conversation_id=conversation_id,
                    )
                    await message.answer(
                        "✅ Диалог завершён.\n\n"
                        "🧠 Бот запомнил этот ответ и в следующий раз ответит сам!"
                    )
                else:
                    await message.answer("✅ Диалог завершён. Жду новых уведомлений.")
            else:
                await message.answer("✅ Диалог завершён. Жду новых уведомлений.")
        else:
            await message.answer("✅ Диалог завершён. Жду новых уведомлений.")
        return

    # Проверяем, отвечает ли менеджер на диалог
    conversation_id = get_operator_replying(operator_telegram_id)
    if not conversation_id:
        await message.answer(
            "💡 Вы в режиме менеджера.\n"
            "Когда гостю понадобится помощь — я пришлю уведомление с кнопкой 'Ответить'."
        )
        return

    # Получаем диалог и клиента
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        clear_operator_replying(operator_telegram_id)
        await message.answer("❌ Диалог не найден. Возможно, он был закрыт.")
        return

    result = await session.execute(
        select(Client).where(Client.id == conversation.client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        clear_operator_replying(operator_telegram_id)
        await message.answer("❌ Клиент не найден.")
        return

    # Сохраняем сообщение менеджера
    await save_message(session, conversation_id, MessageSender.operator, message.text)
    await session.commit()

    # Отправляем ответ клиенту (Telegram или WhatsApp)
    try:
        if client.channel == ChannelType.whatsapp:
            # Клиент из WhatsApp — отправляем через wappi.pro или Meta
            from app.bot.channels.whatsapp import send_whatsapp_message
            success = await send_whatsapp_message(
                client.channel_user_id, message.text
            )
            if not success:
                raise Exception("Не удалось отправить в WhatsApp")
        else:
            # Клиент из Telegram
            await message.bot.send_message(
                chat_id=client.channel_user_id,
                text=message.text,
            )

        channel_name = "WhatsApp" if client.channel == ChannelType.whatsapp else "Telegram"
        await message.answer(
            f"✅ Ответ отправлен гостю ({channel_name})!\n\n"
            "Можете написать ещё или выбрать шаблон:",
            reply_markup=_build_operator_reply_keyboard(conversation_id),
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения клиенту: {e}")
        await message.answer(f"❌ Ошибка отправки: {e}")


async def handle_client_message(message: types.Message, session):
    """Обработка сообщения от клиента."""
    # 1. Найти или создать клиента
    client = await get_or_create_client(
        session=session,
        channel=ChannelType.telegram,
        channel_user_id=str(message.from_user.id),
        name=message.from_user.full_name,
        username=message.from_user.username,
    )

    # 2. Найти активный диалог или создать новый
    conversation = await get_active_conversation(session, client.id)
    is_new_conversation = conversation is None
    if not conversation:
        conversation = await create_conversation(session, client.id)

    # 3. Сохранить сообщение клиента
    await save_message(
        session, conversation.id, MessageSender.client, message.text
    )

    # 3.1. Извлечь и сохранить телефон, если есть
    await extract_and_save_phone(session, client.id, message.text)

    # 4. Если диалог ведёт оператор или ждёт менеджера — уведомить его
    if conversation.status in (ConversationStatus.operator_active, ConversationStatus.needs_operator):
        if conversation.assigned_operator_id:
            from app.db.models.models import Operator
            op_result = await session.execute(
                select(Operator).where(Operator.id == conversation.assigned_operator_id)
            )
            assigned_operator = op_result.scalar_one_or_none()
            if assigned_operator and assigned_operator.telegram_id:
                try:
                    await message.bot.send_message(
                        chat_id=assigned_operator.telegram_id,
                        text=f"💬 Новое сообщение от гостя (диалог #{conversation.id}):\n\n{message.text}",
                    )
                except Exception as e:
                    logger.error(f"Ошибка уведомления менеджера: {e}")
        return

    # 4.5. Прайс-лист — отправляем картинку
    from app.bot.channels.whatsapp import _is_price_request, PRICE_IMAGE_PATH
    if _is_price_request(message.text):
        import os
        if os.path.exists(PRICE_IMAGE_PATH):
            from aiogram.types import FSInputFile
            try:
                photo = FSInputFile(PRICE_IMAGE_PATH)
                await message.answer_photo(photo, caption="Прайс-лист отеля Тон Азур 😊")
                await save_message(session, conversation.id, MessageSender.bot, "[Прайс-лист отправлен]")
                await session.commit()
                return
            except Exception as e:
                logger.error(f"Ошибка отправки прайс-картинки в Telegram: {e}")

    # 5. Показываем "печатает..." пока думаем
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # 6. Ищем подсказку в базе знаний (но НЕ отвечаем ей напрямую)
    knowledge_hint = None
    history = await get_conversation_history(session, conversation.id)
    msg_count = len([m for m in history if m.sender == MessageSender.client])

    # KB используем только для первых сообщений — в середине диалога AI лучше справится с контекстом
    if msg_count <= 2:
        knowledge_entry = await search_knowledge_base(session, message.text)
        if knowledge_entry:
            knowledge_hint = f"Вопрос: {knowledge_entry.question}\nОтвет: {knowledge_entry.answer}"
            logger.info(f"KB hint (id={knowledge_entry.id}): '{knowledge_entry.question[:60]}'")

    # 6.5. Проверяем доступность через Exely и передаём в промпт
    all_messages = await get_conversation_history(session, conversation.id, limit=20)
    availability_text = await check_and_format_availability(all_messages)
    if availability_text:
        knowledge_hint = (knowledge_hint or "") + f"\n\n=== ДАННЫЕ ИЗ СИСТЕМЫ БРОНИРОВАНИЯ ===\n{availability_text}\n=== ИСПОЛЬЗУЙ ЭТИ ДАННЫЕ В ОТВЕТЕ ==="

    # 7. Генерируем ответ через AI (с подсказкой из KB если есть)
    previous_context = await get_client_previous_messages(
        session, client.id, conversation.id
    )
    response_text = await generate_response(history, previous_context, knowledge_hint)

    # Извлекаем категорию из ответа AI или из текста клиента
    category = extract_category(response_text)
    if not category:
        category = detect_category_from_text(message.text)
    if category and conversation.category == ConversationCategory.general:
        try:
            conversation.category = ConversationCategory(category)
        except ValueError:
            pass

    # Проверяем нужен ли менеджер
    need_operator = needs_operator(response_text)

    # Программная проверка: если собраны все данные для брони — эскалируем
    if not need_operator:
        booking_check = extract_booking_data(all_messages)
        if booking_check.checkin and booking_check.phone and booking_check.adults:
            need_operator = True
            logger.info(f"Авто-эскалация: бронь готова (даты+телефон+гости)")

    if need_operator:
        conversation.status = ConversationStatus.needs_operator
    elif bot_completed(response_text):
        conversation.status = ConversationStatus.bot_completed

    response_text = clean_response(response_text)

    # Проверяем и исправляем цены + добавляем варианты
    response_text = fix_prices_in_response(response_text, all_messages)
    response_text = ensure_room_variants(response_text, all_messages)

    # Если нужен менеджер — отправить уведомление
    if need_operator:
        booking_data = None
        try:
            all_msgs = await get_conversation_history(session, conversation.id, limit=20)
            booking_data = extract_booking_data(all_msgs)
        except Exception as e:
            logger.error(f"Ошибка извлечения данных бронирования: {e}")

        await session.commit()
        await notify_operators_new_request(
            bot=message.bot,
            session=session,
            conversation=conversation,
            client=client,
            last_message=message.text,
            booking_data=booking_data,
        )

    # 7. Сохранить ответ бота
    await save_message(
        session, conversation.id, MessageSender.bot, response_text
    )

    await session.commit()

    # 8. Отправить ответ клиенту
    await message.answer(response_text)


async def start_bot():
    """Запуск Telegram бота (polling)."""
    global bot, dp

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан — бот не запущен")
        return

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Telegram бот запускается...")
    await dp.start_polling(bot)


def get_bot() -> Bot | None:
    """Получить экземпляр бота (для отправки из админки)."""
    return bot


async def stop_bot():
    """Остановка Telegram бота."""
    global bot, dp
    if dp:
        await dp.stop_polling()
    if bot:
        await bot.session.close()
    logger.info("Telegram бот остановлен")
