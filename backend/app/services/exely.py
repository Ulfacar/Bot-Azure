"""Сервис интеграции с Exely — проверка доступности и бронирование."""

import logging
from dataclasses import dataclass
from datetime import date

from app.core.config import settings
from app.exely_client.client import ExelyClient, ExelyApiException
from app.exely_client.schemas import (
    HotelAvailabilityRequestParams,
    HotelAvailabilityCriterion,
    HotelAvailabilityCriterionHotel,
    HotelAvailabilityResponse,
    HotelReservationRequest,
    HotelReservationRequestItem,
    HotelReservationResponse,
    HotelRef,
    RoomStayReservation,
    RoomTypeReservation,
    RoomTypeReservationPlacement,
    RatePlanReservation,
    GuestCountInfoAPI,
    GuestCountDetailAPI,
    GuestInfo,
    GuestPlacementRef,
    GuaranteeReservation,
    CustomerReservation,
    CustomerContactInfo,
    CustomerContactPhone,
    CustomerContactEmail,
    DateRangeStay,
    CancelReservationRequestPayload,
    CancelHotelReservationRef,
    CancelReservationVerification,
)

logger = logging.getLogger(__name__)

# Синглтон клиента
_client: ExelyClient | None = None


def get_exely_client() -> ExelyClient | None:
    """Получить экземпляр Exely клиента."""
    global _client
    if not settings.exely_api_key:
        return None
    if _client is None:
        _client = ExelyClient(api_key=settings.exely_api_key)
    return _client


@dataclass
class RoomOption:
    """Упрощённый вариант номера для отображения гостю."""
    room_type_code: str
    room_type_name: str
    rate_plan_code: str
    total_price: float
    currency: str
    nights: int
    price_per_night: float
    free_cancellation: bool
    guarantee_code: str


async def check_availability(
    checkin: date,
    checkout: date,
    adults: int,
    children_ages: list[int] | None = None,
) -> list[RoomOption]:
    """Проверить доступность номеров на даты.

    Возвращает список доступных вариантов (упрощённых для бота).
    """
    client = get_exely_client()
    if not client:
        logger.warning("Exely не настроен — пропускаем проверку доступности")
        return []

    hotel_code = settings.exely_hotel_code
    if not hotel_code:
        logger.warning("EXELY_HOTEL_CODE не задан")
        return []

    dates_str = f"{checkin.isoformat()};{checkout.isoformat()}"
    children_str = ",".join(str(a) for a in children_ages) if children_ages else None
    nights = (checkout - checkin).days

    request = HotelAvailabilityRequestParams(
        language="ru",
        currency="KGS",
        include_transfers=False,
        include_rates=True,
        include_all_placements=True,
        criterions=[
            HotelAvailabilityCriterion(
                ref="0",
                hotels=[HotelAvailabilityCriterionHotel(code=hotel_code)],
                dates=dates_str,
                adults=adults,
                children=children_str,
            )
        ],
    )

    try:
        response = await client.get_availability(request)
    except ExelyApiException as e:
        logger.error(f"Ошибка проверки доступности Exely: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка Exely: {e}")
        return []

    # Получаем информацию об отеле для имён типов номеров
    room_names = await _get_room_type_names(hotel_code)

    options: list[RoomOption] = []
    for room_stay in response.room_stays:
        # Берём первый guarantee code
        guarantee_code = room_stay.guarantees[0].code if room_stay.guarantees else ""

        for room_type in room_stay.room_types:
            for rate_plan in room_stay.rate_plans:
                # Считаем цену для этой комбинации room_type + rate_plan
                total = 0.0
                currency = "KGS"
                for pr in room_stay.placement_rates:
                    if pr.room_type_code == room_type.code and pr.rate_plan_code == rate_plan.code:
                        for daily in pr.rates:
                            total += daily.price_after_tax
                            currency = daily.currency

                if total <= 0:
                    # Используем общую цену room_stay
                    total = room_stay.total.price_after_tax
                    currency = room_stay.total.currency

                name = room_names.get(room_type.code, room_type.code)
                price_per_night = total / nights if nights > 0 else total

                options.append(RoomOption(
                    room_type_code=room_type.code,
                    room_type_name=name,
                    rate_plan_code=rate_plan.code,
                    total_price=total,
                    currency=currency,
                    nights=nights,
                    price_per_night=price_per_night,
                    free_cancellation=rate_plan.cancel_penalty_group.free_cancellation or False,
                    guarantee_code=guarantee_code,
                ))

    # Убираем дубликаты по room_type_code (оставляем самый дешёвый)
    seen: dict[str, RoomOption] = {}
    for opt in options:
        if opt.room_type_code not in seen or opt.total_price < seen[opt.room_type_code].total_price:
            seen[opt.room_type_code] = opt

    result = sorted(seen.values(), key=lambda o: o.total_price)
    logger.info(f"Exely: найдено {len(result)} вариантов на {checkin}—{checkout}, {adults} взр.")
    return result


# Кэш имён типов номеров
_room_names_cache: dict[str, str] = {}


async def _get_room_type_names(hotel_code: str) -> dict[str, str]:
    """Получить маппинг code → name для типов номеров."""
    global _room_names_cache
    if _room_names_cache:
        return _room_names_cache

    client = get_exely_client()
    if not client:
        return {}

    try:
        info = await client.get_hotel_info(hotel_code, language="ru")
        hotels = info.get("hotels", [])
        if hotels:
            for rt in hotels[0].get("room_types", []):
                _room_names_cache[rt["code"]] = rt.get("name", rt["code"])
        logger.info(f"Exely: загружено {len(_room_names_cache)} типов номеров")
    except Exception as e:
        logger.error(f"Ошибка загрузки hotel_info: {e}")

    return _room_names_cache


def format_availability_for_bot(options: list[RoomOption]) -> str:
    """Форматировать результаты доступности для ответа бота."""
    if not options:
        return ""

    lines = ["📋 Доступные номера на ваши даты:\n"]
    for i, opt in enumerate(options, 1):
        cancel_text = "✅ бесплатная отмена" if opt.free_cancellation else ""
        lines.append(
            f"{i}. **{opt.room_type_name}**\n"
            f"   {opt.total_price:,.0f} {opt.currency} за {opt.nights} ноч. "
            f"({opt.price_per_night:,.0f} {opt.currency}/ночь)"
            + (f" — {cancel_text}" if cancel_text else "")
        )

    lines.append(
        "\nКакой номер вас заинтересовал? Для бронирования мне понадобятся ваше имя и номер телефона 😊"
    )
    return "\n".join(lines)


def format_availability_for_telegram(options: list[RoomOption]) -> str:
    """Форматировать для Telegram (без Markdown)."""
    if not options:
        return ""

    lines = ["📋 Доступные номера на ваши даты:\n"]
    for i, opt in enumerate(options, 1):
        cancel_text = " (бесплатная отмена)" if opt.free_cancellation else ""
        lines.append(
            f"{i}. {opt.room_type_name}\n"
            f"   {opt.total_price:,.0f} {opt.currency} за {opt.nights} ноч. "
            f"({opt.price_per_night:,.0f} {opt.currency}/ночь){cancel_text}"
        )

    lines.append(
        "\nКакой номер вас заинтересовал? Для бронирования мне понадобятся ваше имя и номер телефона 😊"
    )
    return "\n".join(lines)


async def create_booking(
    checkin: date,
    checkout: date,
    adults: int,
    room_type_code: str,
    rate_plan_code: str,
    guarantee_code: str,
    guest_first_name: str,
    guest_last_name: str,
    phone: str,
    email: str = "tonazure.hotel@gmail.com",
    children_ages: list[int] | None = None,
) -> HotelReservationResponse | None:
    """Создать бронирование в Exely."""
    client = get_exely_client()
    if not client:
        return None

    hotel_code = settings.exely_hotel_code

    # Формируем placements для гостей
    placements = [
        RoomTypeReservationPlacement(index=0, kind="adult", code="adult_bed")
    ]
    guest_counts = [
        GuestCountDetailAPI(count=adults, age_qualifying_code="adult", placement_index=0)
    ]
    guests = [
        GuestInfo(
            placement=GuestPlacementRef(index=0),
            first_name=guest_first_name,
            last_name=guest_last_name,
        )
    ]

    if children_ages:
        for idx, age in enumerate(children_ages, 1):
            placements.append(
                RoomTypeReservationPlacement(index=idx, kind="child", code="child_bed")
            )
            guest_counts.append(
                GuestCountDetailAPI(
                    count=1,
                    age_qualifying_code="child",
                    placement_index=idx,
                    age=age,
                )
            )

    request = HotelReservationRequest(
        language="ru",
        currency="KGS",
        hotel_reservations=[
            HotelReservationRequestItem(
                hotel_ref=HotelRef(code=hotel_code),
                room_stays=[
                    RoomStayReservation(
                        stay_dates=DateRangeStay(
                            start_date=f"{checkin.isoformat()} 14:00:00",
                            end_date=f"{checkout.isoformat()} 12:00:00",
                        ),
                        room_types=[
                            RoomTypeReservation(
                                code=room_type_code,
                                placements=placements,
                            )
                        ],
                        rate_plans=[RatePlanReservation(code=rate_plan_code)],
                        guest_count_info=GuestCountInfoAPI(
                            guest_counts=guest_counts,
                            adults=adults,
                            children=len(children_ages) if children_ages else 0,
                        ),
                        guests=guests,
                    )
                ],
                guarantee=GuaranteeReservation(
                    code=guarantee_code,
                    success_url="https://www.tonazure-hotel.com/booking/success",
                    decline_url="https://www.tonazure-hotel.com/booking/decline",
                ),
                customer=CustomerReservation(
                    first_name=guest_first_name,
                    last_name=guest_last_name,
                    confirm_sms=True,
                    subscribe_email=False,
                    contact_info=CustomerContactInfo(
                        phones=[CustomerContactPhone(phone_number=phone)],
                        emails=[CustomerContactEmail(email_address=email)],
                    ),
                ),
            )
        ],
    )

    try:
        response = await client.create_reservation(request)
        if response.hotel_reservations:
            res = response.hotel_reservations[0]
            logger.info(
                f"Exely: бронь создана #{res.number}, статус={res.status}, "
                f"сумма={res.total.price_after_tax} {res.total.currency}"
            )
        return response
    except ExelyApiException as e:
        logger.error(f"Ошибка создания бронирования: {e}")
        return None


async def cancel_booking(
    booking_number: str,
    cancellation_code: str,
) -> bool:
    """Отменить бронирование в Exely."""
    client = get_exely_client()
    if not client:
        return False

    request = CancelReservationRequestPayload(
        language="ru",
        hotel_reservation_refs=[
            CancelHotelReservationRef(
                number=booking_number,
                verification=CancelReservationVerification(
                    cancellation_code=cancellation_code,
                ),
            )
        ],
    )

    try:
        response = await client.cancel_reservation(request)
        if response.hotel_reservations:
            status = response.hotel_reservations[0].status
            logger.info(f"Exely: бронь {booking_number} отменена, статус={status}")
            return status in ("cancelled", "canceled")
        return False
    except ExelyApiException as e:
        logger.error(f"Ошибка отмены бронирования {booking_number}: {e}")
        return False
