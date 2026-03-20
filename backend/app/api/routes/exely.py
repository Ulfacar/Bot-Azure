"""API-эндпоинты для Exely PMS (проверка доступности)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_operator
from app.services.exely import check_availability, RoomAvailability

router = APIRouter(prefix="/exely", tags=["exely"])


class AvailabilityRequest(BaseModel):
    checkin: date
    checkout: date
    adults: int = 2


class AvailabilityItem(BaseModel):
    room_type_id: str
    room_type_name: str
    total_rooms: int
    occupied_rooms: int
    free_rooms: int
    max_guests: int
    price_per_night: int
    currency: str


@router.get("/debug")
async def debug_exely(_=Depends(get_current_operator)):
    """Debug: проверить подключение к PMS API."""
    from app.services.exely import get_exely_client
    from app.core.config import settings
    import traceback

    result = {
        "exely_api_key_set": bool(settings.exely_api_key),
        "exely_api_key_prefix": settings.exely_api_key[:8] + "..." if settings.exely_api_key else "",
    }

    client = get_exely_client()
    if not client:
        result["error"] = "Client is None"
        return result

    try:
        rooms = await client.get_rooms()
        result["rooms_count"] = len(rooms)
    except Exception as e:
        result["rooms_error"] = f"{type(e).__name__}: {e}"

    try:
        bookings = await client.search_bookings(
            state="Active",
            affects_period_from="2026-03-25T00:00",
            affects_period_to="2026-03-27T00:00",
        )
        result["bookings_count"] = len(bookings)
    except Exception as e:
        result["bookings_error"] = f"{type(e).__name__}: {e}"

    try:
        from datetime import date
        from app.services.exely import check_availability
        options = await check_availability(date(2026, 3, 25), date(2026, 3, 27), 2)
        result["availability_count"] = len(options)
        result["availability"] = [
            {"name": o.room_type_name, "free": o.free_rooms}
            for o in options
        ]
    except Exception as e:
        result["availability_error"] = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

    return result


@router.post("/availability", response_model=list[AvailabilityItem])
async def api_check_availability(
    req: AvailabilityRequest,
    _=Depends(get_current_operator),
):
    """Проверить доступность номеров через PMS API."""
    if req.checkin >= req.checkout:
        raise HTTPException(400, "Дата выезда должна быть позже даты заезда")
    if req.adults < 1:
        raise HTTPException(400, "Минимум 1 взрослый гость")

    options = await check_availability(req.checkin, req.checkout, req.adults)
    return [
        AvailabilityItem(
            room_type_id=o.room_type_id,
            room_type_name=o.room_type_name,
            total_rooms=o.total_rooms,
            occupied_rooms=o.occupied_rooms,
            free_rooms=o.free_rooms,
            max_guests=o.max_guests,
            price_per_night=o.price_per_night,
            currency=o.currency,
        )
        for o in options
    ]
