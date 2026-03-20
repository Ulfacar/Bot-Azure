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
