"""
Скрипт для создания тестовых диалогов в БД.

Запуск на VPS:
  cd /root/Bot-Azure/backend
  DATABASE_URL="postgresql+asyncpg://..." python -m scripts.seed_test_dialogs

Или локально (с docker-compose):
  DATABASE_URL="postgresql+asyncpg://postgres:hotel_secure_2026@localhost:5433/hotel" \
  python -m scripts.seed_test_dialogs
"""
import asyncio
import sys
import os

# Добавляем путь к backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.models.models import (
    Client, Conversation, Message, Booking,
    ChannelType, ConversationStatus, ConversationCategory,
    MessageSender,
)


DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL не задан. Установите переменную окружения.")
    sys.exit(1)


engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def ts(minutes_ago: int) -> datetime:
    """Время N минут назад (naive, без timezone)."""
    return datetime.utcnow() - timedelta(minutes=minutes_ago)


async def create_dialog(
    session: AsyncSession,
    client_data: dict,
    conversation_data: dict,
    messages: list[dict],
    booking_data: dict | None = None,
):
    """Создать клиента, диалог, сообщения и опционально бронь."""
    client = Client(**client_data)
    session.add(client)
    await session.flush()

    conv = Conversation(client_id=client.id, **conversation_data)
    session.add(conv)
    await session.flush()

    for msg in messages:
        m = Message(conversation_id=conv.id, **msg)
        session.add(m)

    if booking_data:
        booking = Booking(
            conversation_id=conv.id,
            client_id=client.id,
            **booking_data,
        )
        session.add(booking)

    await session.flush()
    return client, conv


async def seed():
    async with async_session() as session:
        async with session.begin():

            # ============================================================
            # 1. ЗАВЕРШЁННОЕ БРОНИРОВАНИЕ (closed) — полный цикл
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "Айбек Каримов",
                    "phone": "+996700111222",
                    "username": "aibek_k",
                    "channel": ChannelType.telegram,
                    "channel_user_id": "test_100001",
                    "created_at": ts(180),
                },
                conversation_data={
                    "status": ConversationStatus.closed,
                    "category": ConversationCategory.booking,
                    "created_at": ts(180),
                    "updated_at": ts(120),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Здравствуйте! Хочу забронировать номер", "created_at": ts(180)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! Благодарим за обращение в Тон Азур 😊 Подскажите, на какие даты и сколько гостей вы планируете?", "created_at": ts(179)},
                    {"sender": MessageSender.client, "text": "На 15-20 июня, нас будет 2 человека", "created_at": ts(175)},
                    {"sender": MessageSender.bot, "text": "Проверил наличие! На ваши даты доступны:\n\n1. Twin/Double comfort (двухместный)\n   9,000 KGS/ночь (45,000 KGS за 5 ноч.)\n   Свободно: 10 из 12, до 2 гостей\n\n2. Triple comfort (трёхместный)\n   12,500 KGS/ночь (62,500 KGS за 5 ноч.)\n   Свободно: 3 из 3, до 3 гостей\n\nКакой тип номера вам подойдёт? Подскажите ваше ФИО для бронирования 😊", "created_at": ts(174)},
                    {"sender": MessageSender.client, "text": "Twin подойдёт. Айбек Каримов", "created_at": ts(170)},
                    {"sender": MessageSender.bot, "text": "Отлично, Айбек! Подскажите контактный телефон для связи?", "created_at": ts(169)},
                    {"sender": MessageSender.client, "text": "+996 700 111 222", "created_at": ts(165)},
                    {"sender": MessageSender.bot, "text": "Спасибо, Айбек! Давайте подтвердим детали:\n\n📅 Заезд: 15 июня 2026\n📅 Выезд: 20 июня 2026 (5 ночей)\n👥 Гостей: 2\n🏨 Номер: Twin/Double comfort\n💰 Стоимость: 45,000 KGS\n\nУсловия отмены: бесплатно за 48ч, иначе предоплата не возвращается.\n\nПередаю менеджеру для подтверждения брони!", "created_at": ts(164)},
                    {"sender": MessageSender.operator, "text": "Здравствуйте, Айбек! Бронь создана. Для подтверждения, пожалуйста, внесите предоплату 30% (13,500 KGS).\n\nРеквизиты:\n💳 Перевод на карту: 4169 5851 0312 7890\n📱 QR-код: будет отправлен отдельно\n\n⚠️ Наличный расчёт не принимается.", "created_at": ts(140)},
                    {"sender": MessageSender.client, "text": "Хорошо, оплачу сегодня. Спасибо!", "created_at": ts(135)},
                    {"sender": MessageSender.operator, "text": "Отлично! Ждём подтверждение оплаты. Хорошего дня! 😊", "created_at": ts(130)},
                ],
                booking_data={
                    "category": "booking",
                    "details": "Twin/Double comfort, 15-20 июня 2026, 2 гостя, 45000 KGS",
                    "confirmed": True,
                    "created_at": ts(164),
                },
            )

            # ============================================================
            # 2. ОЖИДАЕТ МЕНЕДЖЕРА (needs_operator) — заявка на бронь
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "Мария Соколова",
                    "phone": "+996555333444",
                    "channel": ChannelType.whatsapp,
                    "channel_user_id": "996555333444",
                    "created_at": ts(45),
                },
                conversation_data={
                    "status": ConversationStatus.needs_operator,
                    "category": ConversationCategory.booking,
                    "created_at": ts(45),
                    "updated_at": ts(30),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Добрый день! Ищу отель на Иссык-Куле на начало июля", "created_at": ts(45)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! Благодарим за обращение в Тон Азур 😊 Мы бутик-отель на первой линии с панорамным видом на Иссык-Куль. Подскажите точные даты и количество гостей?", "created_at": ts(44)},
                    {"sender": MessageSender.client, "text": "С 1 по 7 июля, семья — 2 взрослых и ребёнок 5 лет", "created_at": ts(40)},
                    {"sender": MessageSender.bot, "text": "Отличный выбор! На ваши даты доступны:\n\n1. Triple comfort (трёхместный) — 12,500 KGS/ночь (75,000 KGS за 6 ноч.)\n   Свободно: 3 из 3\n\n2. Family comfort (четырёхместный) — 15,700 KGS/ночь (94,200 KGS за 6 ноч.)\n   Свободно: 2 из 2\n\nДля ребёнка 5 лет детская кроватка бесплатно 😊 Какой тип номера предпочитаете?", "created_at": ts(39)},
                    {"sender": MessageSender.client, "text": "Family, пожалуйста. Мария Соколова, +996 555 333 444", "created_at": ts(35)},
                    {"sender": MessageSender.bot, "text": "Спасибо, Мария! Подтверждаю детали:\n\n📅 1-7 июля 2026 (6 ночей)\n👥 2 взрослых + ребёнок\n🏨 Family comfort\n💰 94,200 KGS\n🛏️ Детская кроватка: бесплатно\n\nПередаю менеджеру для подтверждения брони!", "created_at": ts(34)},
                ],
                booking_data={
                    "category": "booking",
                    "details": "Family comfort, 1-7 июля 2026, 2 взрослых + ребёнок, 94200 KGS",
                    "confirmed": False,
                    "created_at": ts(34),
                },
            )

            # ============================================================
            # 3. БОТ ВЕДЁТ ДИАЛОГ (in_progress) — клиент спрашивает
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "Дмитрий",
                    "username": "dima_travel",
                    "channel": ChannelType.telegram,
                    "channel_user_id": "test_100003",
                    "created_at": ts(15),
                },
                conversation_data={
                    "status": ConversationStatus.in_progress,
                    "category": ConversationCategory.booking,
                    "created_at": ts(15),
                    "updated_at": ts(5),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Привет! Какие у вас цены на август?", "created_at": ts(15)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! Благодарим за обращение в Тон Азур 😊 Август — высокий сезон, вот наши цены:\n\n• Single Comfort — 6,800 KGS/ночь\n• Twin/Double — 9,000 KGS/ночь\n• Triple — 12,500 KGS/ночь\n• Family — 15,700 KGS/ночь\n\nЗавтрак включён в стоимость. Подскажите, на какие даты планируете?", "created_at": ts(14)},
                    {"sender": MessageSender.client, "text": "А есть скидки если на 10 дней?", "created_at": ts(10)},
                    {"sender": MessageSender.bot, "text": "При длительном проживании возможна индивидуальная скидка 10-20%. Точные условия зависят от дат и загрузки. Подскажите конкретные даты, и я проверю наличие? 😊", "created_at": ts(9)},
                    {"sender": MessageSender.client, "text": "1-10 августа, на двоих", "created_at": ts(5)},
                    {"sender": MessageSender.bot, "text": "Проверил! На 1-10 августа (9 ночей) доступны:\n\n1. Twin/Double comfort — 9,000 KGS/ночь (81,000 KGS за 9 ноч.)\n   Свободно: 8 из 12\n\n2. Triple comfort — 12,500 KGS/ночь (112,500 KGS за 9 ноч.)\n   Свободно: 2 из 3\n\nДля бронирования подскажите ваше ФИО и контактный телефон?", "created_at": ts(4)},
                ],
            )

            # ============================================================
            # 4. МЕНЕДЖЕР АКТИВЕН (operator_active) — обсуждение деталей
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "ООО ТурМакс",
                    "phone": "+996312555666",
                    "channel": ChannelType.whatsapp,
                    "channel_user_id": "996312555666",
                    "created_at": ts(120),
                },
                conversation_data={
                    "status": ConversationStatus.operator_active,
                    "category": ConversationCategory.booking,
                    "created_at": ts(120),
                    "updated_at": ts(10),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Здравствуйте, это турагентство ТурМакс. Нужно разместить группу из 8 человек на 20-25 июля", "created_at": ts(120)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! Благодарим за обращение в Тон Азур 😊 Для группы из 8 человек на 20-25 июля доступны:\n\n• Twin/Double: 11 свободных (до 2 гостей) — 9,000 KGS/ночь\n• Triple: 3 свободных (до 3 гостей) — 12,500 KGS/ночь\n• Family: 2 свободных (до 4 гостей) — 15,700 KGS/ночь\n\nДля корпоративных клиентов предусмотрены специальные условия. Подскажите, какую комбинацию номеров предпочитаете?", "created_at": ts(119)},
                    {"sender": MessageSender.client, "text": "Нам нужно 3 Twin и 1 Family. Также нужен трансфер из аэропорта Манас на 8 человек и конференц-зал на полдня", "created_at": ts(115)},
                    {"sender": MessageSender.bot, "text": "Отличный выбор! По трансферу из аэропорта Манас — стоимость 10,000 KGS. Конференц-зал вмещает до 30 человек. Для корпоративных условий и группового бронирования передаю вас менеджеру — он подготовит индивидуальное предложение.", "created_at": ts(114)},
                    {"sender": MessageSender.operator, "text": "Здравствуйте! Спасибо за обращение. Для группы из 8 человек предлагаем:\n\n3× Twin/Double: 9,000 × 5 ноч. × 3 = 135,000 KGS\n1× Family: 15,700 × 5 ноч. = 78,500 KGS\nТрансфер: 10,000 KGS\nКонференц-зал (полдня): 15,000 KGS\n\nИТОГО: 238,500 KGS\n\nПри групповом бронировании скидка 10%: 214,650 KGS\n\nМожем оформить договор и счёт для юрлица. Подтверждаете?", "created_at": ts(90)},
                    {"sender": MessageSender.client, "text": "Цена устраивает. Нужен договор и счёт-фактура на ООО ТурМакс, ИНН 01234567890123", "created_at": ts(60)},
                    {"sender": MessageSender.operator, "text": "Принято! Подготовлю документы сегодня и отправлю на почту. Подскажите email для отправки?", "created_at": ts(55)},
                    {"sender": MessageSender.client, "text": "info@tourmax.kg", "created_at": ts(10)},
                ],
                booking_data={
                    "category": "booking",
                    "details": "ГРУППА: 3×Twin + 1×Family, 20-25 июля 2026, 8 чел, трансфер+конференц-зал, 214650 KGS со скидкой 10%",
                    "confirmed": False,
                    "created_at": ts(114),
                },
            )

            # ============================================================
            # 5. ОБЩИЙ ВОПРОС — бот справился сам (bot_completed)
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "Алина",
                    "username": "alina_kg",
                    "channel": ChannelType.telegram,
                    "channel_user_id": "test_100005",
                    "created_at": ts(90),
                },
                conversation_data={
                    "status": ConversationStatus.bot_completed,
                    "category": ConversationCategory.hotel,
                    "created_at": ts(90),
                    "updated_at": ts(80),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Здравствуйте! Есть ли у вас бассейн?", "created_at": ts(90)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! Благодарим за обращение в Тон Азур 😊 Да, у нас есть открытый бассейн с подогревом — он работает бесплатно для всех гостей. Также есть терраса на 3 этаже с панорамным видом на Иссык-Куль ☀️ Могу ещё чем-то помочь?", "created_at": ts(89)},
                    {"sender": MessageSender.client, "text": "А парковка есть?", "created_at": ts(85)},
                    {"sender": MessageSender.bot, "text": "Да, парковка бесплатная для гостей! Также у нас Wi-Fi по всему отелю, бесплатный трансфер до пляжей летом, детская площадка и прачечная. Что-нибудь ещё?", "created_at": ts(84)},
                    {"sender": MessageSender.client, "text": "Спасибо, всё понятно!", "created_at": ts(80)},
                    {"sender": MessageSender.bot, "text": "Рады помочь! Если решите забронировать — пишите, будем рады видеть вас в Тон Азур 🏨", "created_at": ts(79)},
                ],
            )

            # ============================================================
            # 6. ВОПРОС ОБ УСЛУГАХ (closed, service)
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "Нурлан Асанов",
                    "phone": "+996770999888",
                    "channel": ChannelType.whatsapp,
                    "channel_user_id": "996770999888",
                    "created_at": ts(300),
                },
                conversation_data={
                    "status": ConversationStatus.closed,
                    "category": ConversationCategory.service,
                    "created_at": ts(300),
                    "updated_at": ts(270),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Салам! Какие экскурсии есть?", "created_at": ts(300)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! Благодарим за обращение в Тон Азур 😊 У нас можно организовать:\n\n🐎 Конные прогулки\n🏔️ Поездки к каньонам (Сказка — 28 км, Барскоон — 54 км)\n⛵ Яхтенные прогулки\n🚴 Велосипедные прогулки\n🎨 Мастер-классы\n\nРядом пляж Кекилик (1.5 км) и Боконбаево (7 км). Что-то конкретное интересует?", "created_at": ts(299)},
                    {"sender": MessageSender.client, "text": "А трансфер из Бишкека сколько стоит?", "created_at": ts(290)},
                    {"sender": MessageSender.bot, "text": "Трансфер из аэропорта Манас — 10,000 сом. Из Бишкека до отеля примерно 278 км, это 4-4.5 часа на авто. Также можем организовать трансфер из аэропорта Тамчи — стоимость рассчитывается индивидуально. Подсказать что-нибудь ещё?", "created_at": ts(289)},
                    {"sender": MessageSender.client, "text": "Рахмат! Потом напишу для брони", "created_at": ts(275)},
                    {"sender": MessageSender.bot, "text": "Жакшы! Ждём вас в Тон Азур, пишите когда будете готовы 🏨😊", "created_at": ts(274)},
                ],
            )

            # ============================================================
            # 7. ЭСКАЛАЦИЯ — нестандартный запрос (needs_operator)
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "Елена Петрова",
                    "username": "elena_p",
                    "channel": ChannelType.telegram,
                    "channel_user_id": "test_100007",
                    "created_at": ts(60),
                },
                conversation_data={
                    "status": ConversationStatus.needs_operator,
                    "category": ConversationCategory.general,
                    "created_at": ts(60),
                    "updated_at": ts(50),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Здравствуйте! У нас свадьба на 40 человек в августе. Можно ли провести банкет в вашем ресторане и забронировать весь отель?", "created_at": ts(60)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! Благодарим за обращение в Тон Азур 😊 Какое прекрасное событие! В нашем отеле 17 номеров, ресторан с национальной и европейской кухней, а также конференц-зал до 30 человек. Для организации свадебного банкета на 40 человек потребуется индивидуальный расчёт. Передаю ваш запрос менеджеру — он свяжется с вами в ближайшее время!", "created_at": ts(59)},
                ],
            )

            # ============================================================
            # 8. ПОВТОРНЫЙ КЛИЕНТ — новый диалог (in_progress)
            # ============================================================
            await create_dialog(
                session,
                client_data={
                    "name": "Азамат Тойчиев",
                    "phone": "+996550777888",
                    "username": "azamat_t",
                    "channel": ChannelType.telegram,
                    "channel_user_id": "test_100008",
                    "created_at": ts(500),
                },
                conversation_data={
                    "status": ConversationStatus.closed,
                    "category": ConversationCategory.booking,
                    "created_at": ts(500),
                    "updated_at": ts(450),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Салам! Хочу номер на 1-3 мая", "created_at": ts(500)},
                    {"sender": MessageSender.bot, "text": "Здравствуйте! На ваши даты есть свободные номера. Подскажите ваше ФИО и телефон?", "created_at": ts(499)},
                    {"sender": MessageSender.client, "text": "Азамат Тойчиев, +996 550 777 888", "created_at": ts(495)},
                    {"sender": MessageSender.bot, "text": "Передаю менеджеру для подтверждения!", "created_at": ts(494)},
                    {"sender": MessageSender.operator, "text": "Бронь подтверждена! Ждём вас 1 мая 😊", "created_at": ts(460)},
                ],
                booking_data={
                    "category": "booking",
                    "details": "Twin/Double, 1-3 мая 2026, 2 ночи",
                    "confirmed": True,
                    "created_at": ts(494),
                },
            )
            # Второй диалог того же клиента (новая бронь)
            # Используем того же клиента по channel_user_id
            # Для простоты создаём как отдельную запись — в реальности
            # get_or_create_client найдёт существующего
            await create_dialog(
                session,
                client_data={
                    "name": "Азамат Тойчиев",
                    "phone": "+996550777888",
                    "username": "azamat_t",
                    "channel": ChannelType.telegram,
                    "channel_user_id": "test_100008b",
                    "created_at": ts(20),
                },
                conversation_data={
                    "status": ConversationStatus.in_progress,
                    "category": ConversationCategory.booking,
                    "created_at": ts(20),
                    "updated_at": ts(8),
                },
                messages=[
                    {"sender": MessageSender.client, "text": "Привет! Хочу опять к вам, теперь на июль", "created_at": ts(20)},
                    {"sender": MessageSender.bot, "text": "С возвращением, Азамат! 😊 Рады снова видеть вас. Подскажите точные даты в июле и количество гостей?", "created_at": ts(19)},
                    {"sender": MessageSender.client, "text": "10-15 июля, опять на двоих", "created_at": ts(12)},
                    {"sender": MessageSender.bot, "text": "Проверил! На 10-15 июля (5 ночей) доступны:\n\n1. Twin/Double comfort — 9,000 KGS/ночь (45,000 KGS)\n   Свободно: 7 из 12\n\nОтличный выбор! Подскажите актуальный телефон для связи?", "created_at": ts(11)},
                ],
            )

        await session.commit()
        print("✅ Создано 9 тестовых диалогов:")
        print("   1. Завершённое бронирование (closed, booking)")
        print("   2. Ожидает менеджера — семья (needs_operator, booking)")
        print("   3. Бот ведёт диалог — цены (in_progress, booking)")
        print("   4. Менеджер активен — турагентство (operator_active, booking)")
        print("   5. Бот справился — бассейн/парковка (bot_completed, hotel)")
        print("   6. Закрытый — экскурсии/трансфер (closed, service)")
        print("   7. Ожидает менеджера — свадьба (needs_operator, general)")
        print("   8. Повторный клиент — старая бронь (closed)")
        print("   9. Повторный клиент — новая бронь (in_progress)")


if __name__ == "__main__":
    asyncio.run(seed())
