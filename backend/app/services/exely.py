"""Сервис интеграции с Exely PMS — проверка доступности номеров."""

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

from app.core.config import settings
from app.exely_client.client import ExelyPMSClient, ExelyApiException
from app.exely_client.schemas import PMSRoom, PMSBooking, PMSRoomStay

logger = logging.getLogger(__name__)

# Синглтон клиента
_client: ExelyPMSClient | None = None

# Маппинг roomTypeId → название категории
ROOM_TYPE_NAMES = {
    "5064615": "Twin/Double comfort (двухместный)",
    "5064616": "Triple comfort (трёхместный)",
    "5064617": "Triple comfort (трёхместный)",
    "5064618": "Family comfort (четырёхместный)",
}

# Маппинг roomTypeId → макс. гостей
ROOM_TYPE_CAPACITY = {
    "5064615": 2,
    "5064616": 3,
    "5064617": 3,
    "5064618": 4,
}

# Количество номеров по типу (из данных PMS)
ROOM_TYPE_TOTAL = {
    "5064615": 12,  # Twin/Double
    "5064616": 1,   # Triple
    "5064617": 2,   # Triple
    "5064618": 2,   # Family
}


def get_exely_client() -> ExelyPMSClient | None:
    """Получить экземпляр Exely PMS клиента."""
    global _client
    if not settings.exely_api_key:
        return None
    if _client is None:
        _client = ExelyPMSClient(api_key=settings.exely_api_key)
    return _client


def _get_season_price(room_type_id: str, checkin: date) -> int | None:
    """Получить цену за ночь по сезону и типу номера."""
    month, day = checkin.month, checkin.day

    # Определяем сезон
    if (month == 6 and day >= 1) or (month in (7, 8)) or (month == 9 and day <= 15):
        season = "high"       # 1 июн — 15 сен
    elif (month >= 2 and month <= 5) or (month == 1 and day == 31):
        season = "mid_spring"  # 1 фев — 31 мая
    elif (month == 9 and day >= 16) or (month == 10) or (month == 11 and day <= 15):
        season = "mid_autumn"  # 16 сен — 15 ноя
    else:
        season = "low"        # 16 ноя — 31 янв

    prices = {
        # roomTypeId: {season: price_per_night}
        "5064615": {"low": 6000, "mid_spring": 8000, "high": 9000, "mid_autumn": 8000},
        "5064616": {"low": 9000, "mid_spring": 11000, "high": 12500, "mid_autumn": 11000},
        "5064617": {"low": 9000, "mid_spring": 11000, "high": 12500, "mid_autumn": 11000},
        "5064618": {"low": 10000, "mid_spring": 14000, "high": 15700, "mid_autumn": 14000},
    }

    type_prices = prices.get(room_type_id)
    if not type_prices:
        return None
    return type_prices.get(season)


@dataclass
class RoomAvailability:
    """Доступность номеров по категории."""
    room_type_id: str
    room_type_name: str
    total_rooms: int
    occupied_rooms: int
    free_rooms: int
    max_guests: int
    price_per_night: int
    currency: str = "KGS"


async def check_availability(
    checkin: date,
    checkout: date,
    adults: int = 2,
) -> list[RoomAvailability]:
    """Проверить доступность номеров на даты через PMS API.

    Логика: получаем все активные брони на период → считаем занятые номера
    по типу → вычитаем из общего количества.
    """
    client = get_exely_client()
    if not client:
        logger.warning("Exely PMS не настроен — пропускаем проверку доступности")
        return []

    try:
        # Ищем активные брони, пересекающиеся с периодом
        period_from = f"{checkin.isoformat()}T00:00"
        period_to = f"{checkout.isoformat()}T00:00"

        booking_numbers = await client.search_bookings(
            state="Active",
            affects_period_from=period_from,
            affects_period_to=period_to,
        )

        # Считаем занятые номера по типу
        occupied_by_type: Counter[str] = Counter()

        for bn in booking_numbers:
            try:
                booking_data = await client.get_booking(bn)
                booking = PMSBooking.model_validate(booking_data)

                for rs in booking.roomStays:
                    # Проверяем что roomStay действительно пересекается с нашим периодом
                    # и не отменён
                    if rs.bookingStatus == "Cancelled":
                        continue
                    rs_checkin = datetime.fromisoformat(rs.checkInDateTime).date()
                    rs_checkout = datetime.fromisoformat(rs.checkOutDateTime).date()
                    if rs_checkin < checkout and rs_checkout > checkin:
                        occupied_by_type[rs.roomTypeId] += 1

            except ExelyApiException as e:
                logger.error(f"Ошибка получения брони {bn}: {e}")
                continue

        # Формируем результат по каждому типу номера
        results: list[RoomAvailability] = []

        # Группируем 5064616 и 5064617 как Triple
        triple_total = ROOM_TYPE_TOTAL.get("5064616", 0) + ROOM_TYPE_TOTAL.get("5064617", 0)
        triple_occupied = occupied_by_type.get("5064616", 0) + occupied_by_type.get("5064617", 0)
        triple_free = triple_total - triple_occupied

        for type_id, total in ROOM_TYPE_TOTAL.items():
            if type_id == "5064617":
                # Уже посчитан вместе с 5064616
                continue

            if type_id == "5064616":
                free = triple_free
                total_count = triple_total
                occupied = triple_occupied
            else:
                occupied = occupied_by_type.get(type_id, 0)
                free = total - occupied
                total_count = total

            if free <= 0:
                continue

            price = _get_season_price(type_id, checkin)
            if not price:
                continue

            name = ROOM_TYPE_NAMES.get(type_id, f"Тип {type_id}")
            capacity = ROOM_TYPE_CAPACITY.get(type_id, 2)

            results.append(RoomAvailability(
                room_type_id=type_id,
                room_type_name=name,
                total_rooms=total_count,
                occupied_rooms=occupied,
                free_rooms=free,
                max_guests=capacity,
                price_per_night=price,
            ))

        # Сортируем по цене
        results.sort(key=lambda r: r.price_per_night)

        logger.info(
            f"Exely PMS: {checkin}—{checkout}, {adults} гост. | "
            f"Брони: {len(booking_numbers)}, свободных категорий: {len(results)}"
        )
        return results

    except ExelyApiException as e:
        logger.error(f"Ошибка проверки доступности Exely PMS: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка Exely PMS: {e}")
        return []


def format_availability_for_telegram(options: list[RoomAvailability], nights: int) -> str:
    """Форматировать результаты доступности для Telegram."""
    if not options:
        return ""

    lines = ["Доступные номера на ваши даты:\n"]
    for i, opt in enumerate(options, 1):
        total_price = opt.price_per_night * nights
        lines.append(
            f"{i}. {opt.room_type_name}\n"
            f"   {opt.price_per_night:,} {opt.currency}/ночь "
            f"({total_price:,} {opt.currency} за {nights} ноч.)\n"
            f"   Свободно: {opt.free_rooms} из {opt.total_rooms}, до {opt.max_guests} гостей"
        )

    return "\n".join(lines)


def format_availability_short(options: list[RoomAvailability]) -> str:
    """Короткий формат — просто подтверждение наличия (для физлиц)."""
    if not options:
        return ""

    total_free = sum(o.free_rooms for o in options)
    return f"На ваши даты есть свободные номера (всего {total_free} свободных)."
