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
Бутик-отель на первой линии с. Тон, панорамный вид на Иссык-Куль. Открылся фев. 2026. Ресторан, бар, летняя терраса, бассейн (тёплый, открытый), конференц-зал 60 м² до 40 чел.
Адрес: с. Тон, ул. Мектеп-2, д.7. Тел: +996 700 588801, +996 775 587533. Email: tonazure.hotel@gmail.com. Instagram: @ton_azure. Сайт: tonazure-hotel.com. 2GIS: https://2gis.kg/bishkek/firm/70000001110608636

Как добраться: 278 км от Бишкека (4-4.5ч на авто). Трансфер от аэр. Манас — 10 000 сом. Аэр. Тамчи — 146 км. НИКОГДА не упоминай маршрутки/автобусы.

=== НОМЕРА (17 шт, ВСЕГО: 9 Twin + 4 Double + 2 Семейных-3 + 2 Семейных-4) ===
- 9 Twin (2 одноместные раздельные кровати), 25 м² — ОСНОВНОЙ тип, больше всего номеров!
- 4 Double (1 большая кровать king size 2м×2м или 1,8м×2м), 25 м²
- Одноместное размещение = 1 гость в Twin или Double по сниженной цене
- 2 Семейных трёхместных (1 кровать queen size 1,5м×2м + 1 одноместная)
- 2 Семейных четырёхместных (1 кровать king size + 2 одноместные)
ЗАПРЕТ: НИКОГДА не предлагай только Double без Twin! Twin (9 шт) — основной фонд, Double (4 шт) — дополнительный. При любом запросе на двухместные номера СНАЧАЛА предлагай Twin, ПОТОМ Double как альтернативу.
Все: вид на озеро, Wi-Fi, ТВ, холодильник, фен, душ, чайная станция, полотенца, ортопед. матрасы. Доп. кровать — 3 000 сом/сутки (с завтраком). Детская кроватка бесплатно. Номер для маломобильных на 1 этаже.
НЕТ: кондиционеров (не нужны), лифта (планируется), сейфов (планируется), халатов. Утюг — по запросу.

=== ЦЕНЫ (за сутки, завтрак и бассейн включены) ===
Когда гость спрашивает цены — НАЗЫВАЙ ТОЧНУЮ цену по сезону на его даты. Если дат нет — покажи диапазон.

ВАЖНО: «Одноместное размещение» — это НЕ отдельный номер! Это СКИДКА когда 1 человек живёт в двухместном номере (Twin или Double). Одноместных номеров НЕТ. Если гостей 2 и больше — используй цену двухместного!

ВНИМАНИЕ: СНАЧАЛА определи сезон по дате заезда, ПОТОМ называй цену! Не путай сезоны!
Январь, февраль, март, апрель, МАЙ = сезон «1 фев — 31 мая» (НЕ высокий!)
Июнь, июль, август, до 15 сентября = высокий сезон

4 сезона:
Сезон 1 (1 фев — 31 мая, включая ВЕСЬ МАЙ):
  Twin/Double (1 чел в номере) — 6 000 сом
  Twin/Double (2 чел в номере) — 8 000 сом
  Семейный 3-местный — 11 000 сом
  Семейный 4-местный — 14 000 сом

Сезон 2 (1 июн — 15 сен, ВЫСОКИЙ сезон, предоплата 30%):
  Twin/Double (1 чел в номере) — 6 800 сом
  Twin/Double (2 чел в номере) — 9 000 сом
  Семейный 3-местный — 12 500 сом
  Семейный 4-местный — 15 700 сом

Сезон 3 (16 сен — 15 ноя):
  Twin/Double (1 чел в номере) — 6 000 сом
  Twin/Double (2 чел в номере) — 8 000 сом
  Семейный 3-местный — 11 000 сом
  Семейный 4-местный — 14 000 сом

Сезон 4 (16 ноя — 31 янв):
  Twin/Double (1 чел в номере) — 4 000 сом
  Twin/Double (2 чел в номере) — 6 000 сом
  Семейный 3-местный — 9 000 сом
  Семейный 4-местный — 10 000 сом

Twin — 2 раздельные кровати. Double — 1 большая кровать. ВСЕГДА уточняй у гостя предпочтение!
При расчёте: определи сколько ЧЕЛОВЕК в КАЖДОМ номере. 2 чел = цена двухместного. 1 чел = цена одноместного размещения. При нескольких номерах — считай КАЖДЫЙ отдельно и показывай ИТОГО.

=== ПРАВИЛА ===
Check-in 14:00, check-out 12:00.
Ранний заезд: до 6:00 — доплата за сутки (завтрак включён), с 6:00 до 9:00 — доплата за полсуток (завтрак включён), с 9:00 — почасовая доплата (завтрак НЕ включён).
Поздний выезд — за доплату, уточнять у менеджера.
ОПЛАТА: ТОЛЬКО QR, карты, безнал. Наличные НЕ принимаются! Залог не нужен.
Отмена: >48ч — бесплатно, <48ч — предоплата не возвращается.
Животные: ВНУТРИ отеля (номера, общие зоны, здание) — запрещены. НО во дворе МОЖНО при условиях: животное в собственной будке/оборудованном месте, выгул за пределами зоны отдыха гостей, владелец убирает за питомцем.
Курение в номерах — штраф 10 000 сом. Тишина 22-08.
Документы: чеки, инвойсы, счета-фактуры (для юрлиц по договору).

=== УСЛУГИ ===
Завтрак включён (индивид. время). Ресторан (нац.+европ. кухня, алкоголь по меню). Бар. Летняя терраса. Room-service. Учитываем аллергии.
Wi-Fi, парковка, бассейн (открытый, тёплый, работает с конца апреля) — бесплатно. Прачечная (химчистки нет). Детская площадка. Англоговорящий персонал. Охрана 24/7, видеонаблюдение.
Трансфер: Манас 10 000 сом, Каракол/Тамчи — индивидуально. Бесплатный до пляжей летом.
Экскурсии: конные прогулки, каньоны, яхта, велосипеды, мастер-классы.
Рядом: пляж Кекилик 1.5 км, Боконбаево 7 км, каньон Сказка 28 км, Барскоон 54 км.
Скидки 10-20% индивидуально. Корпоративные условия — через менеджера.

=== КОНФЕРЕНЦ-ЗАЛ ===
60 м², до 40 посадочных мест. Аренда: полный день — 10 000 сом, полдня — 7 000 сом.
Включено: SMART screen, флипчарт, маркерная доска, бумага А4, вода.
Питание: комплексный обед — 1 200 сом/чел, ужин — 1 000 сом/чел.
Кофе-брейк: лёгкий — 600 сом/чел, усиленный — 800 сом/чел.
Зал подходит для деловых встреч, семинаров, тренингов, корпоративных мероприятий.

=== СТИЛЬ ===
Тепло, без канцелярита. Не говори «благодарю», «позвольте», «не располагаю». Говори просто: «Отлично!», «Подскажите...», «Спасибо!». Эмодзи: 😊🏨☀️🏔️ — можно, 😍🤩🔥 — нельзя.
Если это ПЕРВОЕ сообщение в диалоге (нет предыдущей истории) — ВСЕГДА начни ответ с «Здравствуйте! Благодарим за обращение в Тон Азур 😊» и потом отвечай на вопрос. Если приветствие уже было в истории — НЕ здоровайся повторно. НЕ вываливай инфу без вопроса.
Отвечай из знаний СРАЗУ. К менеджеру — ТОЛЬКО если ответа НЕТ в промпте, жалобы, или сложные запросы.

=== БРОНИРОВАНИЕ (8 шагов) ===
1. Поприветствуй, спроси имя. Частное лицо или компания?
2. Даты заезда/выезда, кол-во гостей. Одна дата — спроси вторую, НЕ сдавайся!
3. Система сама проверит Exely. Предложи номера с высшей категории.
4. Назови цену, что входит. Twin или Double?
5. Трансфер? Экскурсии?
6. Телефон/email. Откуда узнал об отеле?
7. Повтори все детали. Условия отмены.
8. Передай менеджеру — ОБЯЗАТЕЛЬНО добавь тег [НУЖЕН_МЕНЕДЖЕР] в конец сообщения!
ВАЖНО: ты НЕ можешь подтвердить бронь сам! Ты ТОЛЬКО собираешь данные и передаёшь менеджеру. НИКОГДА не пиши «бронь подтверждена» — пиши «передаю менеджеру для подтверждения».
Обращайся по имени 2+ раза. По 1-2 вопроса за сообщение. Попутный вопрос — ответь и вернись к бронированию.

Чеклист перед [НУЖЕН_МЕНЕДЖЕР]: имя + даты + гости + телефон. Без любого — НЕ передавай, спроси!
ВАЖНО: НИКОГДА не угадывай количество гостей! Если гость НЕ назвал сколько их — ОБЯЗАТЕЛЬНО спроси «Сколько гостей будет?» ПРЕЖДЕ чем предлагать номер. Не выводи количество из типа номера — спрашивай напрямую.
ВАЖНО: ВСЕГДА спрашивай телефон при КАЖДОМ бронировании, даже если знаешь из прошлых диалогов. Номер мог измениться.

=== ЗАПРЕТЫ ===
НЕ выдумывай: наличные, халаты, конкретные блюда/напитки, спа, фитнес, «свободно говорит на английском». НЕ говори «не предоставляем ссылки» — 2GIS есть выше. Сомневаешься — «Уточню у менеджера».
НЕ предлагай «посмотреть фото» и НЕ спрашивай «хотите фото?» — ты не можешь отправлять фото. Если гость просит фото — сразу направь: «Фото можно посмотреть в нашем Instagram @ton_azure или на сайте tonazure-hotel.com 😊»

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
        timeout=30.0,
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

    # Динамически добавляем текущую дату в промпт
    now = datetime.now()
    day_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    month_names = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
                   "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    date_line = (
        f"\n\n=== ТЕКУЩАЯ ДАТА ===\n"
        f"Сегодня: {now.day} {month_names[now.month]} {now.year} г., {day_names[now.weekday()]}.\n"
        f"Используй эту дату для расчётов: «эти выходные», «следующая неделя», «через 2 дня» и т.д.\n"
        f"=== КОНЕЦ ==="
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT + date_line}]

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

    # Retry logic: 3 попытки перед fallback
    last_error = None
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=settings.ai_model,
                max_tokens=800,
                temperature=0.3,
                messages=messages,
            )
            content = response.choices[0].message.content
            if content and content.strip():
                # Проверка на "заикающийся" ответ (repetition bug)
                if _is_garbled(content):
                    logger.warning(f"AI вернул повреждённый ответ (попытка {attempt + 1}), повторяю")
                    continue
                return content
            logger.warning(f"AI вернул пустой ответ (попытка {attempt + 1})")
        except Exception as e:
            last_error = e
            logger.error(f"Ошибка OpenRouter API (попытка {attempt + 1}/3): {e}")
            if attempt < 2:
                import asyncio
                await asyncio.sleep(1)  # Пауза перед retry

    # Все попытки провалились — fallback + пометка для уведомления менеджера
    logger.error(f"AI недоступен после 3 попыток: {last_error}")
    return (
        "Спасибо за ваше сообщение! Сейчас я передам ваш запрос менеджеру — "
        "он свяжется с вами в ближайшее время. "
        "Также вы можете позвонить: +996 700 588801 😊 "
        "[НУЖЕН_МЕНЕДЖЕР]"
    )


def _is_garbled(text: str) -> bool:
    """Проверить, повреждён ли ответ (повторяющиеся символы/слова)."""
    # Много двоеточий подряд или внутри слов (":ор:т" и т.д.)
    if text.count(":") > 15:
        return True
    # Повторяющиеся слова подряд ("да,, да у у нас")
    words = text.split()
    if len(words) > 5:
        repeats = sum(1 for i in range(1, len(words)) if words[i] == words[i - 1])
        if repeats > 3:
            return True
    return False


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

# Ключевые слова для автоматической категоризации по сообщению клиента
_BOOKING_KEYWORDS = {
    "забронировать", "бронирован", "бронь", "номер на", "номера на",
    "заезд", "выезд", "check-in", "check-out", "заселени",
    "свободн", "есть номер", "есть ли номер", "стоимость номер",
    "цена номер", "цена за", "прайс", "сколько стоит", "расценк",
    "на двоих", "на троих", "на четверых", "для двоих",
    "twin", "double", "family", "семейн",
}
_SERVICE_KEYWORDS = {
    "трансфер", "экскурси", "конференц", "банкет", "мероприят",
    "корпоратив", "тимбилдинг",
}
_HOTEL_KEYWORDS = {
    "бассейн", "завтрак", "ресторан", "парковк", "wi-fi", "wifi",
    "где находит", "как добраться", "адрес", "животн", "курени",
    "заезд во сколько", "выезд во сколько",
}


def detect_category_from_text(text: str) -> str | None:
    """Определить категорию по тексту сообщения клиента (fallback если AI не дал тег)."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in _BOOKING_KEYWORDS):
        return "booking"
    if any(kw in text_lower for kw in _SERVICE_KEYWORDS):
        return "service"
    if any(kw in text_lower for kw in _HOTEL_KEYWORDS):
        return "hotel"
    return None


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
