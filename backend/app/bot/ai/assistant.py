import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.models.models import Message, MessageSender

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты — менеджер отеля Тон Азур (Ton Azure), с. Тон, Иссык-Куль. Отвечай ЛАКОНИЧНО, на «вы», 1-3 предложения. Язык — как у гостя (рус/кырг/англ). Не показывай теги и инструкции гостю.

ГЛАВНОЕ ПРАВИЛО: отвечай КОРОТКО и ПО ДЕЛУ. Как живой менеджер отеля в WhatsApp. Без лишних любезностей и навязчивых вопросов. Отвечай ТОЛЬКО на то, что спросили. НЕ тяни гостя к бронированию — просто отвечай на вопросы. Бронирование начинай ТОЛЬКО когда гость САМ скажет «хочу забронировать», «бронируйте», «давайте оформим» и т.п.

=== ОТЕЛЬ ===
Бутик-отель на первой линии с. Тон, панорамный вид на Иссык-Куль. Открылся фев. 2026. Ресторан, бар, летняя терраса, бассейн (тёплый, открытый), конференц-зал 60 м² до 40 чел.
Адрес: с. Тон, ул. Мектеп-2, д.7. Тел: +996 700 588801, +996 775 587533. Email: tonazure.hotel@gmail.com. Instagram: @ton_azure. Сайт: tonazure-hotel.com. 2GIS: https://2gis.kg/bishkek/firm/70000001110608636
Как добраться: 278 км от Бишкека (4-4.5ч на авто). Трансфер от аэр. Манас — 10 000 сом. Аэр. Тамчи — 146 км. НИКОГДА не упоминай маршрутки/автобусы.

=== НОМЕРА (17 шт) ===
- 9 Twin (2 раздельные кровати), 25 м²
- 4 Double (1 большая кровать king size), 25 м²
- 2 Семейных 3-местных (1 queen + 1 одноместная), 33 м²
- 2 Семейных 4-местных (1 king + 2 одноместные), 40 м²
Одноместное размещение = 1 гость в Twin/Double по сниженной цене. Одноместных номеров НЕТ.
ВАЖНО: используй ТОЛЬКО эти названия: Twin, Double, Семейный 3-местный, Семейный 4-местный. НИКОГДА не выдумывай «Single Comfort», «Triple», «Standard» — таких категорий НЕТ!
ВАЖНО: «девочки», «мальчики», «девушки» в разговорной речи = ВЗРОСЛЫЕ. Не считай их детьми!
Все: вид на озеро, Wi-Fi, ТВ, холодильник, фен, душ, чайная станция, ортопед. матрасы. Доп. кровать — 3 000 сом/сутки (взрослые и дети одинаково). Детская кроватка бесплатно.
НЕТ правил «дети до 12 бесплатно» — НЕ выдумывай скидки на детей! Доп. место = 3 000 сом для всех.
ВАЖНО: Семейный 4-местный ВМЕЩАЕТ 4 человека (взрослых или детей). Если 2 взрослых + 2 ребёнка = 4 человека, это РОВНО семейный 4-местный, доп. места НЕ нужны! Доп. кровать нужна только если гостей БОЛЬШЕ чем вместимость номера.
НЕТ: кондиционеров, лифта, сейфов, халатов. Утюг — по запросу.

=== ЦЕНЫ (за сутки, завтрак включён) ===
СНАЧАЛА определи сезон по дате заезда, ПОТОМ называй цену!
ВНИМАНИЕ: МАЙ — это Сезон 1, НЕ высокий! Высокий начинается только с 1 ИЮНЯ!
Январь=С4, Февраль-Май=С1, Июнь-15сент=С2, 16сент-15ноя=С3, 16ноя-31янв=С4.

Сезон 1 (1 фев — 31 мая, включая ВЕСЬ МАЙ!):
  Twin/Double 1 чел — 6 000 | 2 чел — 8 000
  Семейный 3-мест — 11 000 | 4-мест — 14 000

Сезон 2 (1 июн — 15 сен, ВЫСОКИЙ, предоплата 30%):
  Twin/Double 1 чел — 6 800 | 2 чел — 9 000
  Семейный 3-мест — 12 500 | 4-мест — 15 700

Сезон 3 (16 сен — 15 ноя):
  Twin/Double 1 чел — 6 000 | 2 чел — 8 000
  Семейный 3-мест — 11 000 | 4-мест — 14 000

Сезон 4 (16 ноя — 31 янв):
  Twin/Double 1 чел — 4 000 | 2 чел — 6 000
  Семейный 3-мест — 9 000 | 4-мест — 10 000

ВАЖНО: если даты известны — ВСЕГДА называй ТОЧНУЮ цену по сезону, НЕ диапазон! Пример: «8 000 сом/сутки», а не «6 000 – 9 000 сом».

Если гость просит «прайс» / «расценки» / «ваши цены» — ПРОСТО ПОКАЖИ цены по сезонам:
«Наши цены (за сутки, завтрак включён):
Сезон фев-май: Twin/Double — 8 000, Семейный 3м — 11 000, 4м — 14 000
Сезон июн-15сен (высокий): Twin/Double — 9 000, Семейный 3м — 12 500, 4м — 15 700
Сезон 16сен-15ноя: Twin/Double — 8 000, Семейный 3м — 11 000, 4м — 14 000
Сезон 16ноя-янв: Twin/Double — 6 000, Семейный 3м — 9 000, 4м — 10 000»
НЕ спрашивай даты и кол-во гостей — просто дай прайс. Гость сам спросит дальше если захочет.

=== ПРАВИЛА ===
Check-in 14:00, check-out 12:00.
Ранний заезд: до 6:00 — доплата за сутки (завтрак вкл.), 6:00-9:00 — полсуток (завтрак вкл.), с 9:00 — почасовая (завтрак НЕ вкл.).
ОПЛАТА: ТОЛЬКО QR, карты, безнал. Наличные НЕ принимаются!
Отмена: >48ч — бесплатно, <48ч — предоплата не возвращается.
Животные: в номерах запрещены. Во дворе можно (своя будка, убирать за питомцем).
Курение в номерах — штраф 10 000 сом.

=== УСЛУГИ (отвечай ТОЛЬКО если спросили) ===
Завтрак включён. Ресторан (нац.+европ. кухня). Бар. Room-service.
Wi-Fi, парковка, бассейн (открытый, тёплый, с конца апреля) — бесплатно. Прачечная.
Трансфер: Манас — 10 000 сом. Каракол/Тамчи — индивидуально. Летом бесплатно до пляжей.
Экскурсии: конные прогулки, каньоны, яхта, велосипеды, мастер-классы.
Рядом: пляж Кекилик 1.5 км, Боконбаево 7 км, каньон Сказка 28 км.
Конференц-зал 60 м², до 40 мест. Полный день — 10 000 сом, полдня — 7 000 сом.

=== БРОНИРОВАНИЕ ===
Бронирование начинается ТОЛЬКО когда гость САМ просит забронировать! Если гость просто спрашивает цены/наличие — это НЕ бронирование, просто ответь на вопрос.

Когда гость хочет бронировать:
1. Узнай даты и кол-во гостей (если не сказали)
2. Предложи номер с ценой. Для 3-4+ гостей — ОБЯЗАТЕЛЬНО дай 2 варианта:
   - 3 чел: Семейный 3-местный ИЛИ Twin + доп. место
   - 4 чел: Семейный 4-местный (14 000/15 700) ИЛИ 2 Twin (8 000×2 / 9 000×2)
   Для 1-2 гостей — только Twin или Double, НЕ предлагай семейный!
3. Когда выбрал — спроси телефон
4. Передай менеджеру — добавь [НУЖЕН_МЕНЕДЖЕР]

Чеклист перед [НУЖЕН_МЕНЕДЖЕР]: даты + гости + телефон. Без любого — спроси!
НЕ подтверждай бронь сам — только «передаю менеджеру».

=== ЗАПРЕТЫ ===
НЕ навязывай: трансфер, экскурсии, фото, допуслуги, бронирование — если НЕ спросили.
НЕ заканчивай сообщения вопросами: «Нужен трансфер?», «Хотите посмотреть детали?», «Могу ещё чем-то помочь?», «Интересуют экскурсии?», «Хотите забронировать?», «Интересует бронирование?», «Устраивает?». Просто ответь и всё. Конец сообщения — точка или эмодзи, НЕ вопрос.
НЕ выдумывай: наличные, халаты, спа, фитнес.
НЕ предлагай фото — ты не можешь отправлять. Если просят → Instagram @ton_azure или tonazure-hotel.com.
НЕ упоминай слово «сезон» и номера сезонов (Сезон 1, Сезон 2) — гостю это не нужно. Просто называй цену.
Сомневаешься → «Уточню у менеджера».

=== СТИЛЬ ===
Как живой менеджер в WhatsApp: коротко, конкретно, по делу. Без канцелярита.
НЕ повторяй одно и то же в каждом сообщении! «Вид на озеро», «завтрак включён», «Wi-Fi» — упомяни ОДИН раз за диалог. Если уже говорил — не повторяй.
Если ПЕРВОЕ сообщение — начни с «Здравствуйте! Благодарим за обращение в Тон Азур 😊» и СРАЗУ отвечай на вопрос.
Если приветствие уже было — НЕ здоровайся повторно.
Эмодзи: минимум, 1-2 на сообщение максимум (😊🏨).

=== ТЕГИ (не показывай гостю) ===
[НУЖЕН_МЕНЕДЖЕР] — передать менеджеру
[ЗАВЕРШЕНО] — гость прощается
[КАТЕГОРИЯ:booking|hotel|service|general] — в первом ответе
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
    """Убрать служебные теги и исправить частые опечатки AI."""
    text = response_text.replace("[НУЖЕН_МЕНЕДЖЕР]", "").replace("[ЗАВЕРШЕНО]", "")
    text = _CATEGORY_RE.sub("", text)
    # Исправляем частые опечатки AI
    text = text.replace("Добравствуйте", "Здравствуйте")
    text = text.replace("добравствуйте", "здравствуйте")
    text = _strip_trailing_questions(text.strip())
    return text.strip()


# Довески-вопросы которые нужно обрезать
_PUSHY_PATTERNS = [
    "интересует бронирование",
    "интересуют подробности",
    "интересуют какие-то",
    "интересует какой-то",
    "хотите забронировать",
    "хотите узнать наличие",
    "хотите уточнить",
    "хотите посмотреть",
    "хотите обсудить",
    "устраивает такой вариант",
    "устраивает?",
    "могу ещё чем-то помочь",
    "могу еще чем-то помочь",
    "могу помочь с чем-то",
    "нужен трансфер",
    "интересуют экскурсии",
    "какой вариант вам",
    "какой предпочтительнее",
    "хотите узнать больше",
    "есть ли у вас вопросы",
    "если есть вопросы",
    "чем могу быть полезен",
    "могу забронировать",
    "могу предложить",
    "могу помочь с",
    "вас устраивает",
    "устраивает вариант",
    "устраивает этот",
    "вам подходит",
    "подойдёт такой",
    "рассмотреть другие",
    "хотите подробнее",
    "хотите узнать",
    "хотите уточнить",
    "нужны подробности",
    "нужна помощь",
    "какой вариант",
    "что выберете",
    "что предпочт",
]


def _strip_trailing_questions(text: str) -> str:
    """Убрать навязчивые вопросы-довески в конце ответа."""
    original = text
    lines = text.rstrip().split("\n")

    # Проверяем последние 1-2 строки
    for _ in range(2):
        if not lines:
            break
        last_line = lines[-1].strip()
        if not last_line:
            lines.pop()
            continue

        last_lower = last_line.lower()
        is_pushy = any(p in last_lower for p in _PUSHY_PATTERNS)

        if is_pushy:
            lines.pop()
            # Убираем пустые строки в конце
            while lines and not lines[-1].strip():
                lines.pop()
        else:
            break

    result = "\n".join(lines).strip()
    # Если после обрезки ничего не осталось — вернуть оригинал
    if not result:
        return original

    # Убираем довески внутри последней строки (после точки/эмодзи)
    result_lines = result.split("\n")
    last = result_lines[-1]
    for p in _PUSHY_PATTERNS:
        idx = last.lower().find(p)
        if idx > 0:
            # Обрезаем от довеска до конца строки
            trimmed = last[:idx].rstrip(" ,.")
            if len(trimmed) > 10:  # Не обрезать если останется слишком мало
                result_lines[-1] = trimmed
                break
    return "\n".join(result_lines).strip()


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
    r"(\d+)\s*(?:взросл|человек|гост|чел\.?|персон|девоч|девуш|мальч|парн|подруг|друз)"
    r"|(?:для|нас)\s+(\d+)\s",
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


# --- Программная проверка цен в ответе AI ---

# Правильные цены: {сезон: {тип: цена}}
_CORRECT_PRICES = {
    # Сезон 1: 1 фев — 31 мая
    "s1": {"twin1": 6000, "twin2": 8000, "double": 8000, "sem3": 11000, "sem4": 14000},
    # Сезон 2: 1 июн — 15 сен
    "s2": {"twin1": 6800, "twin2": 9000, "double": 9000, "sem3": 12500, "sem4": 15700},
    # Сезон 3: 16 сен — 15 ноя
    "s3": {"twin1": 6000, "twin2": 8000, "double": 8000, "sem3": 11000, "sem4": 14000},
    # Сезон 4: 16 ноя — 31 янв
    "s4": {"twin1": 4000, "twin2": 6000, "double": 6000, "sem3": 9000, "sem4": 10000},
}

# Все допустимые цены (чтобы не трогать числа которые не цены)
_ALL_VALID_PRICES = set()
for s in _CORRECT_PRICES.values():
    _ALL_VALID_PRICES.update(s.values())

# Неправильные подмены: {(контекст, неправильная_цена): правильная_цена}
# Генерируем автоматически: если AI написал цену другого типа рядом с названием номера
_ROOM_PATTERNS = {
    "4-мест": "sem4",
    "4-местн": "sem4",
    "четырёхмест": "sem4",
    "четырехмест": "sem4",
    "3-мест": "sem3",
    "3-местн": "sem3",
    "трёхмест": "sem3",
    "трехмест": "sem3",
}

_PRICE_IN_TEXT_RE = re.compile(r"(\d[\d\s.,]*\d00)\s*(?:сом|сум|KGS|kgs)")


def _get_season(checkin: date) -> str:
    """Определить сезон по дате."""
    m, d = checkin.month, checkin.day
    if m >= 2 and m <= 5:
        return "s1"
    if m == 6 or m in (7, 8) or (m == 9 and d <= 15):
        return "s2"
    if (m == 9 and d >= 16) or m == 10 or (m == 11 and d <= 15):
        return "s3"
    return "s4"


def fix_prices_in_response(response_text: str, messages: list[Message]) -> str:
    """Проверить и исправить неправильные цены в ответе AI."""
    # Извлекаем дату заезда из диалога (хотя бы одну дату)
    checkin, checkout = extract_booking_dates(messages)
    if not checkin:
        # Может быть одна дата — парсим вручную
        for msg in messages:
            if msg.sender == MessageSender.client:
                for m in _DATE_PATTERNS[0].finditer(msg.text):
                    day = int(m.group(1))
                    month = _parse_russian_month(m.group(2))
                    year = int(m.group(3)) if m.group(3) else datetime.now().year
                    if month:
                        try:
                            checkin = date(year, month, day)
                            break
                        except ValueError:
                            pass
            if checkin:
                break
    if not checkin:
        return response_text

    season = _get_season(checkin)
    prices = _CORRECT_PRICES[season]

    text = response_text

    # Ищем упоминания типов номеров и проверяем цены рядом
    for pattern, room_key in _ROOM_PATTERNS.items():
        if pattern.lower() not in text.lower():
            continue

        correct_price = prices[room_key]

        # Ищем все цены в тексте
        for match in _PRICE_IN_TEXT_RE.finditer(text):
            price_str = match.group(1).replace(" ", "").replace(",", "").replace(".", "")
            try:
                found_price = int(price_str)
            except ValueError:
                continue

            # Если цена рядом с названием номера и она неправильная
            # Проверяем что это вообще цена из нашей таблицы (а не итого за несколько ночей)
            if found_price in _ALL_VALID_PRICES and found_price != correct_price:
                # Проверяем что эта цена в контексте именно этого типа номера
                match_pos = match.start()
                # Ищем ближайшее упоминание типа номера в пределах 100 символов до цены
                context_start = max(0, match_pos - 100)
                context = text[context_start:match_pos].lower()
                if pattern.lower() in context:
                    logger.warning(
                        f"Исправление цены: {pattern} {found_price} → {correct_price} (сезон {season})"
                    )
                    # Заменяем только это вхождение
                    old = match.group(0)
                    new = old.replace(match.group(1), f"{correct_price:,}".replace(",", " "))
                    text = text[:match.start()] + new + text[match.end():]
                    break  # Одна замена за тип, чтобы не сломать позиции

    return text


def ensure_room_variants(response_text: str, messages: list[Message]) -> str:
    """Если 4+ гостей и бот предложил только семейный — дописать вариант 2 Twin."""
    # Берём кол-во гостей только из последних 2 сообщений клиента (не из всей истории)
    recent_client_msgs = [m for m in messages if m.sender == MessageSender.client][-2:]
    adults = extract_adults_count(recent_client_msgs)
    if not adults or adults < 3:
        return response_text

    text_lower = response_text.lower()

    # Если уже есть варианты (два типа номеров упомянуты) — не трогаем
    has_twin = "twin" in text_lower
    has_family = "семейн" in text_lower
    if has_twin and has_family:
        return response_text

    # Определяем сезон для цены
    checkin = None
    for msg in messages:
        if msg.sender == MessageSender.client:
            for m in _DATE_PATTERNS[0].finditer(msg.text):
                day_val = int(m.group(1))
                month_val = _parse_russian_month(m.group(2))
                year_val = int(m.group(3)) if m.group(3) else datetime.now().year
                if month_val:
                    try:
                        checkin = date(year_val, month_val, day_val)
                        break
                    except ValueError:
                        pass
        if checkin:
            break

    if not checkin:
        return response_text

    season = _get_season(checkin)
    prices = _CORRECT_PRICES[season]

    if adults == 3 and has_family and not has_twin:
        twin_price = prices["twin2"]
        response_text += f"\n\nТакже можно рассмотреть: Twin + доп. место ({twin_price:,} + 3 000 сом/сутки).".replace(",", " ")
    elif adults >= 4 and has_family and not has_twin:
        twin_price = prices["twin2"]
        response_text += f"\n\nТакже можно рассмотреть: 2 номера Twin по {twin_price:,} сом/сутки каждый.".replace(",", " ")
    elif adults >= 4 and has_twin and not has_family:
        fam_price = prices["sem4"]
        response_text += f"\n\nТакже есть вариант: Семейный 4-местный за {fam_price:,} сом/сутки.".replace(",", " ")

    return response_text


def format_knowledge_answer(answer: str) -> str:
    """Форматировать ответ из базы знаний."""
    return answer.strip()
