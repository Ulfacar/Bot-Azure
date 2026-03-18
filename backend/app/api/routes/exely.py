"""API-эндпоинты для Exely (бронирование)."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_operator
from app.services.exely import (
    check_availability,
    create_booking,
    cancel_booking,
    RoomOption,
)

router = APIRouter(prefix="/exely", tags=["exely"])


class AvailabilityRequest(BaseModel):
    checkin: date
    checkout: date
    adults: int = 2
    children_ages: list[int] | None = None


class AvailabilityItem(BaseModel):
    room_type_code: str
    room_type_name: str
    rate_plan_code: str
    total_price: float
    currency: str
    nights: int
    price_per_night: float
    free_cancellation: bool
    guarantee_code: str


class BookingRequest(BaseModel):
    checkin: date
    checkout: date
    adults: int
    room_type_code: str
    rate_plan_code: str
    guarantee_code: str
    guest_first_name: str
    guest_last_name: str
    phone: str
    email: str = "tonazure.hotel@gmail.com"
    children_ages: list[int] | None = None


class BookingResponse(BaseModel):
    booking_number: str
    cancellation_code: str
    status: str
    total_price: float
    currency: str
    order_url: str | None = None


class CancelRequest(BaseModel):
    booking_number: str
    cancellation_code: str


@router.post("/availability", response_model=list[AvailabilityItem])
async def api_check_availability(
    req: AvailabilityRequest,
    _=Depends(get_current_operator),
):
    """Проверить доступность номеров (для админки)."""
    if req.checkin >= req.checkout:
        raise HTTPException(400, "Дата выезда должна быть позже даты заезда")
    if req.adults < 1:
        raise HTTPException(400, "Минимум 1 взрослый гость")

    options = await check_availability(
        req.checkin, req.checkout, req.adults, req.children_ages
    )
    return [
        AvailabilityItem(
            room_type_code=o.room_type_code,
            room_type_name=o.room_type_name,
            rate_plan_code=o.rate_plan_code,
            total_price=o.total_price,
            currency=o.currency,
            nights=o.nights,
            price_per_night=o.price_per_night,
            free_cancellation=o.free_cancellation,
            guarantee_code=o.guarantee_code,
        )
        for o in options
    ]


@router.post("/book", response_model=BookingResponse)
async def api_create_booking(
    req: BookingRequest,
    _=Depends(get_current_operator),
):
    """Создать бронирование в Exely (для админки)."""
    if req.checkin >= req.checkout:
        raise HTTPException(400, "Дата выезда должна быть позже даты заезда")

    response = await create_booking(
        checkin=req.checkin,
        checkout=req.checkout,
        adults=req.adults,
        room_type_code=req.room_type_code,
        rate_plan_code=req.rate_plan_code,
        guarantee_code=req.guarantee_code,
        guest_first_name=req.guest_first_name,
        guest_last_name=req.guest_last_name,
        phone=req.phone,
        email=req.email,
        children_ages=req.children_ages,
    )

    if not response or not response.hotel_reservations:
        raise HTTPException(502, "Не удалось создать бронирование в Exely")

    res = response.hotel_reservations[0]
    return BookingResponse(
        booking_number=res.number,
        cancellation_code=res.cancellation_code,
        status=res.status,
        total_price=res.total.price_after_tax,
        currency=res.total.currency,
        order_url=str(res.order_url) if res.order_url else None,
    )


@router.post("/cancel")
async def api_cancel_booking(
    req: CancelRequest,
    _=Depends(get_current_operator),
):
    """Отменить бронирование."""
    success = await cancel_booking(req.booking_number, req.cancellation_code)
    if not success:
        raise HTTPException(502, "Не удалось отменить бронирование")
    return {"status": "cancelled", "booking_number": req.booking_number}
