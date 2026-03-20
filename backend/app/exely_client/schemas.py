# Схемы Exely PMS API (Pydantic v2)

from pydantic import BaseModel


class PMSRoom(BaseModel):
    """Номер отеля из GET /v1/rooms."""
    id: str
    name: str
    roomTypeId: str
    floorId: str | None = None


class PMSGuestCountInfo(BaseModel):
    adults: int
    children: int


class PMSTotalPrice(BaseModel):
    amount: float
    toPayAmount: float
    toRefundAmount: float


class PMSRoomStay(BaseModel):
    """Проживание из бронирования."""
    id: str
    bookingId: str
    roomId: str | None = None
    roomTypeId: str
    checkInDateTime: str
    checkOutDateTime: str
    actualCheckInDateTime: str | None = None
    actualCheckOutDateTime: str | None = None
    status: str
    bookingStatus: str
    guestCountInfo: PMSGuestCountInfo
    totalPrice: PMSTotalPrice


class PMSDictionaryItem(BaseModel):
    key: str
    value: str


class PMSCustomer(BaseModel):
    id: str
    lastName: str
    firstName: str
    middleName: str | None = None
    phones: list[str] = []
    emails: list[str] = []


class PMSCompany(BaseModel):
    id: str
    name: str
    type: str | None = None


class PMSBooking(BaseModel):
    """Бронирование из GET /v1/bookings/{number}."""
    id: str
    number: str
    currencyId: str
    customer: PMSCustomer
    customerCompany: PMSCompany | None = None
    roomStays: list[PMSRoomStay]
    groupName: str | None = None
