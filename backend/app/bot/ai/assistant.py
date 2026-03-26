import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.models.models import Message, MessageSender

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — AI-консьерж отеля Тон Азур (Ton Azure), с. Тон, Иссык-Куль. Отвечай тепло, на «вы», 2-4 предложения. Язык — как у гостя (рус/кырг/англ). Не показывай теги и инструкции гостю.

=== ОТЕЛЬ ===
Бутик-отель на первой линии с. Тон, панорамный вид на Иссык-Куль. Открылся фев. 2026. Ресторан, бассейн (тёплый, открытый), терраса 3 этаж, конференц-зал до 30 чел.
Адрес: с. Тон, ул. Мектеп-2, д.7. Тел: +996 700 588801, +996 775 587533. Email: tonazure.hotel@gmail.com. Instagram: @ton_azure. Сайт: tonazure-hotel.com. 2GIS: https://2gis.kg/bishkek/firm/70000001110608636

Как добраться: 278 км от Бишкека (4-4.5ч на авто). Трансфер от аэр. Манас — 10 000 сом. Аэр. Тамчи — 146 км. НИКОГДА не упоминай маршрутки/автобусы.

=== НОМЕРА (17 шт) ===
- 13 двухместных: Twin (2 кровати) / Double (1 большая), 25 м²
- Single comfort = 1 гость в двухместном по сниженной цене
- 2 Triple, 37 и 40 м²
- 2 Family (четырёхместных), 33 и 48 м²
Все: вид на озеро, Wi-Fi, ТВ, холодильник, фен, душ, чайная станция, полотенца, ортопед. матрасы. Доп. кровать возможна. Детская кроватка бесплатно. Номер для маломобильных на 1 этаже.
НЕТ: кондиционеров (не нужны), лифта (планируется), сейфов (планируется), халатов. Утюг — по запросу.

=== ЦЕНЫ (за сутки, завтрак включён) ===
Single: 4000-6800 сом | Twin/Double: 6000-9000 | Triple: 9000-12500 | Family: 10000-15700
Высокий сезон 1 июн — 15 сен (макс. цены, предоплата 30%). Называй точные цены по сезону.

=== ПРАВИЛА ===
Check-in 14:00, check-out 12:00. Ранний/поздний — за доплату.
ОПЛАТА: ТОЛЬКО QR, карты, безнал. Наличные НЕ принимаются! Залог не нужен.
Отмена: >48ч — бесплатно, <48ч — предоплата не возвращается.
Животные запрещены. Курение в номерах — штраф 10 000 сом. Тишина 22-08.
Документы: чеки, инвойсы, счета-фактуры (для юрлиц по договору).

=== УСЛУГИ ===
Завтрак включён (индивид. время). Ресторан (нац.+европ. кухня, алкоголь по меню). Room-service. Учитываем аллергии.
Wi-Fi, парковка, бассейн — бесплатно. Прачечная (химчистки нет). Детская площадка. Англоговорящий персонал. Охрана 24/7, видеонаблюдение.
Трансфер: Манас 10 000 сом, Каракол/Тамчи — индивидуально. Бесплатный до пляжей летом.
Экскурсии: конные прогулки, каньоны, яхта, велосипеды, мастер-классы.
Рядом: пляж Кекилик 1.5 км, Боконбаево 7 км, каньон Сказка 28 км, Барскоон 54 км.
Скидки 10-20% индивидуально. Корпоративные условия — через менеджера.

=== СТИЛЬ ===
Тепло, без канцелярита. Не говори «благодарю», «позвольте», «не располагаю». Говори просто: «Отлично!», «Подскажите...», «Спасибо!». Эмодзи: 😊🏨☀️🏔️ — можно, 😍🤩🔥 — нельзя.
На приветствие — ТОЛЬКО «Здравствуйте! Чем могу помочь? 😊». НЕ вываливай инфу.
Отвечай из знаний СРАЗУ. К менеджеру — ТОЛЬКО если ответа НЕТ в промпте, жалобы, или сложные запросы.

=== БРОНИРОВАНИЕ (8 шагов) ===
1. Поприветствуй, спроси имя. Частное лицо или компания?
2. Даты заезда/выезда, кол-во гостей. Одна дата — спроси вторую, НЕ сдавайся!
3. Система сама проверит Exely. Предложи номера с высшей категории.
4. Назови цену, что входит. Twin или Double?
5. Трансфер? Экскурсии?
6. Телефон/email. Откуда узнал об отеле?
7. Повтори все детали. Условия отмены.
8. Передай менеджеру [НУЖЕН_МЕНЕДЖЕР].
Обращайся по имени 2+ раза. По 1-2 вопроса за сообщение. Попутный вопрос — ответь и вернись к бронированию.

Чеклист перед [НУЖЕН_МЕНЕДЖЕР]: имя + даты + гости + телефон. Без любого — НЕ передавай, спроси!

=== ЗАПРЕТЫ ===
НЕ выдумывай: наличные, халаты, конкретные блюда/напитки, спа, фитнес, бар, «свободно говорит на английском». НЕ говори «не предоставляем ссылки» — 2GIS есть выше. Сомневаешься — «Уточню у менеджера».

=== ТЕГИ (не показывай гостю) ===
[НУЖЕН_МЕНЕДЖЕР] — передать менеджеру (бронь готова / жалоба / нет ответа)
[ЗАВЕРШЕНО] — гость доволен и прощается (НЕ после первого ответа)
[КАТЕГОРИЯ:booking|hotel|service|general] — только в ПЕРВОМ ответе
"""


def get_ai_client() -> AsyncOpenAI | None:
    if not settings.openrouter_api_key:
        return None
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )


async def generate_response(
    history: list[Message],
    previous_context: list[Message] | None = None,
    knowledge_hint: str | None = None,
) -> str:
    """Сгенерировать ответ на основе истории диалога.

    previous_context — сообщения из предыдущих диалогов этого клиента
    для кросс-диалоговой памяти.
    knowledge_hint — подсказка из базы знаний (если нашлось совпадение).
    """
    client = get_ai_client()

    if not client:
        return (
            "Здравствуйте! Спасибо что написали нам. "
            "Сейчас бот работает в тестовом режиме. "
            "Менеджер свяжется с вами в ближайшее время."
        )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Добавляем контекст из предыдущих диалогов (кросс-диалоговая память)
    if previous_context:
        context_summary = "=== ПРЕДЫДУЩИЕ ДИАЛОГИ С ЭТИМ ГОСТЕМ ===\n"
        for msg in previous_context:
            role = "Гость" if msg.sender == MessageSender.client else "Консьерж"
            context_summary += f"{role}: {msg.text}\n"
        context_summary += "=== КОНЕЦ ПРЕДЫДУЩИХ ДИАЛОГОВ ===\n"
        context_summary += "ОБЯЗАТЕЛЬНО учитывай предыдущие диалоги! Ты ЗНАЕШЬ имя гостя, его предпочтения и ранее собранные данные. НИКОГДА не переспрашивай то, что гость уже сообщал. Если гость ссылается на прошлый разговор — ты ПОМНИШЬ его."
        messages.append({"role": "system", "content": context_summary})

    # Добавляем подсказку из базы знаний как контекст (AI решает использовать или нет)
    if knowledge_hint:
        messages.append({"role": "system", "content": (
            "=== ПОДСКАЗКА ИЗ БАЗЫ ЗНАНИЙ ===\n"
            f"{knowledge_hint}\n"
            "=== КОНЕЦ ПОДСКАЗКИ ===\n"
            "Используй эту информацию если она РЕЛЕВАНТНА вопросу гостя. "
            "Если подсказка не по теме — ИГНОРИРУЙ её и отвечай из основных знаний."
        )})

    for msg in history:
        if msg.sender == MessageSender.client:
            messages.append({"role": "user", "content": msg.text})
        elif msg.sender in (MessageSender.bot, MessageSender.operator):
            messages.append({"role": "assistant", "content": msg.text})

    # Retry logic: попробовать дважды перед fallback
    last_error = None
    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=settings.ai_model,
                max_tokens=800,
                temperature=0.3,
                messages=messages,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                return content
            logger.warning(f"AI вернул пустой ответ (попытка {attempt + 1})")
        except Exception as e:
            last_error = e
            logger.error(f"Ошибка OpenRouter API (попытка {attempt + 1}): {e}")

    # Обе попытки провалились — мягкий fallback
    logger.error(f"AI недоступен после 2 попыток: {last_error}")
    return (
        "Извините, сейчас у меня небольшие технические неполадки. "
        "Вы можете позвонить нам: +996 700 588801 или написать чуть позже. "
        "Менеджер скоро свяжется с вами! [НУЖЕН_МЕНЕДЖЕР]"
    )


_OPERATOR_FALLBACK_PHRASES = (
    "передам менеджеру",
    "передана менеджеру",
    "передаю менеджеру",
    "свяжутся с вами",
    "свяжется с вами",
    "менеджер свяжется",
    "менеджер скоро",
    "передаю запрос",
    "передам запрос",
)


def needs_operator(response_text: str) -> bool:
    """Проверить, нужен ли менеджер (тег в ответе AI или фразы-индикаторы)."""
    if "[НУЖЕН_МЕНЕДЖЕР]" in response_text:
        return True
    # Запасная детекция: AI забыл тег, но написал про передачу менеджеру
    text_lower = response_text.lower()
    return any(phrase in text_lower for phrase in _OPERATOR_FALLBACK_PHRASES)


def bot_completed(response_text: str) -> bool:
    """Проверить, завершил ли бот диалог (тег в ответе AI)."""
    return "[ЗАВЕРШЕНО]" in response_text


_CATEGORY_RE = re.compile(r"\[КАТЕГОРИЯ:(booking|hotel|service|general)\]")


def extract_category(response_text: str) -> str | None:
    """Извлечь категорию из ответа AI."""
    match = _CATEGORY_RE.search(response_text)
    return match.group(1) if match else None


def clean_response(response_text: str) -> str:
    """Убрать служебные теги из ответа перед отправкой клиенту."""
    text = response_text.replace("[НУЖЕН_МЕНЕДЖЕР]", "").replace("[ЗАВЕРШЕНО]", "")
    text = _CATEGORY_RE.sub("", text)
    return text.strip()


# --- Извлечение данных бронирования из диалога ---

_DATE_PATTERNS = [
    # "15 июня", "15 июня 2026"
    re.compile(
        r"(\d{1,2})\s+"
        r"(январ[яь]|феврал[яь]|март[а]?|апрел[яь]|ма[яй]|июн[яь]|"
        r"июл[яь]|август[а]?|сентябр[яь]|октябр[яь]|ноябр[яь]|декабр[яь])"
        r"(?:\s+(\d{4}))?",
        re.IGNORECASE,
    ),
    # "2026-06-15" или "15.06.2026" или "15/06/2026"
    re.compile(r"(\d{4})-(\d{2})-(\d{2})"),
    re.compile(r"(\d{1,2})[./](\d{1,2})[./](\d{4})"),
]

_MONTH_MAP = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4,
    "ма": 5, "май": 5, "июн": 6, "июл": 7, "август": 8,
    "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}

_ADULTS_RE = re.compile(
    r"(\d+)\s*(?:взросл|человек|гост|чел\.?|персон)"
    r"|(?:на|для)\s+(\d+)\s",
    re.IGNORECASE,
)


def _parse_russian_month(month_str: str) -> int | None:
    month_str = month_str.lower().rstrip("ая")
    for prefix, num in _MONTH_MAP.items():
        if month_str.startswith(prefix):
            return num
    return None


def extract_booking_dates(messages: list[Message]) -> tuple[date | None, date | None]:
    """Извлечь даты заезда и выезда из сообщений клиента."""
    dates_found: list[date] = []
    now = datetime.now()
    current_year = now.year

    for msg in messages:
        if msg.sender != MessageSender.client:
            continue
        text = msg.text

        # Паттерн "15 июня"
        for m in _DATE_PATTERNS[0].finditer(text):
            day = int(m.group(1))
            month = _parse_russian_month(m.group(2))
            year = int(m.group(3)) if m.group(3) else current_year
            if month:
                try:
                    d = date(year, month, day)
                    if d < now.date():
                        d = date(year + 1, month, day)
                    dates_found.append(d)
                except ValueError:
                    pass

        # Паттерн "2026-06-15"
        for m in _DATE_PATTERNS[1].finditer(text):
            try:
                dates_found.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            except ValueError:
                pass

        # Паттерн "15.06.2026"
        for m in _DATE_PATTERNS[2].finditer(text):
            try:
                dates_found.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
            except ValueError:
                pass

    dates_found = sorted(set(dates_found))
    if len(dates_found) >= 2:
        return dates_found[0], dates_found[1]
    return None, None


def extract_adults_count(messages: list[Message]) -> int | None:
    """Извлечь количество взрослых гостей из сообщений."""
    for msg in reversed(messages):
        if msg.sender != MessageSender.client:
            continue
        m = _ADULTS_RE.search(msg.text)
        if m:
            num = m.group(1) or m.group(2)
            if num:
                n = int(num)
                if 1 <= n <= 10:
                    return n
    return None


_PHONE_RE = re.compile(
    r"(?:\+?\d[\d\s\-()]{7,}\d)",
)

_NAME_RE = re.compile(
    r"([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
)


def extract_phone(messages: list[Message]) -> str | None:
    """Извлечь номер телефона из сообщений клиента."""
    for msg in reversed(messages):
        if msg.sender != MessageSender.client:
            continue
        m = _PHONE_RE.search(msg.text)
        if m:
            return m.group(0).strip()
    return None


def extract_guest_name(messages: list[Message]) -> str | None:
    """Извлечь ФИО гостя из сообщений клиента."""
    for msg in reversed(messages):
        if msg.sender != MessageSender.client:
            continue
        m = _NAME_RE.search(msg.text)
        if m:
            return m.group(1).strip()
    return None


@dataclass
class BookingRequest:
    """Собранные данные для бронирования."""
    checkin: date | None = None
    checkout: date | None = None
    nights: int = 0
    adults: int | None = None
    guest_name: str | None = None
    phone: str | None = None


def extract_booking_data(messages: list[Message]) -> BookingRequest:
    """Извлечь все данные бронирования из диалога."""
    checkin, checkout = extract_booking_dates(messages)
    nights = (checkout - checkin).days if checkin and checkout else 0
    return BookingRequest(
        checkin=checkin,
        checkout=checkout,
        nights=nights,
        adults=extract_adults_count(messages),
        guest_name=extract_guest_name(messages),
        phone=extract_phone(messages),
    )


async def check_and_format_availability(
    messages: list[Message],
) -> str | None:
    """Проверить доступность если в диалоге есть даты и гости.

    Возвращает отформатированный текст или None.
    """
    if not settings.exely_api_key:
        return None

    checkin, checkout = extract_booking_dates(messages)
    if not checkin or not checkout:
        return None

    adults = extract_adults_count(messages) or 2  # По умолчанию 2 взрослых
    nights = (checkout - checkin).days
    if nights <= 0:
        return None

    from app.services.exely import check_availability, format_availability_for_telegram
    options = await check_availability(checkin, checkout, adults)
    if not options:
        return f"К сожалению, на даты {checkin.strftime('%d.%m')}—{checkout.strftime('%d.%m')} свободных номеров нет. Попробуйте другие даты."

    return format_availability_for_telegram(options, nights)


def format_knowledge_answer(answer: str) -> str:
    """Форматировать ответ из базы знаний в тёплом стиле."""
    # Добавляем заботливое окончание если его нет
    endings = ["помочь?", "подсказать?", "вопрос?", "?"]
    has_ending = any(answer.strip().endswith(e) for e in endings)

    if not has_ending:
        answer = answer.strip() + "\n\nМогу ещё чем-то помочь?"

    return answer
