# Схемы Exely Distribution API (Pydantic v2)

from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field, AnyHttpUrl, conint, constr
from datetime import datetime


# --- Вспомогательные модели ---

class HotelRef(BaseModel):
    code: str = Field(..., description="Hotel ID.")
    name: Optional[str] = Field(None)
    stay_unit_kind: Optional[str] = Field(None)


class TaxItem(BaseModel):
    amount: float
    code: str


class DiscountInfo(BaseModel):
    basic_before_tax: float
    basic_after_tax: float
    amount: float
    currency: Optional[constr(min_length=3, max_length=3)] = None


class PriceInfo(BaseModel):
    price_before_tax: float
    price_after_tax: float
    currency: constr(min_length=3, max_length=3)
    taxes: List[TaxItem] = Field(default_factory=list)
    discount: Optional[DiscountInfo] = None


class GuaranteeInfo(BaseModel):
    code: str
    primary_guarantee_code: Optional[str] = None
    type: str
    payment_system_code: Optional[str] = None
    name: Optional[str] = None
    payment_url: Optional[AnyHttpUrl] = None


class DateRangeStay(BaseModel):
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


# --- hotel_availability REQUEST ---

class HotelAvailabilityCriterionHotel(BaseModel):
    code: str


class HotelAvailabilityCriterion(BaseModel):
    ref: Optional[str] = "0"
    hotels: List[HotelAvailabilityCriterionHotel] = Field(..., min_length=1)
    dates: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2};\d{4}-\d{2}-\d{2}$")
    adults: conint(ge=0)
    children: Optional[str] = Field(None, pattern=r"^(\d{1,2}(,\d{1,2})*)?$")


class HotelAvailabilityRequestParams(BaseModel):
    include_transfers: bool = False
    language: str = "ru"
    criterions: List[HotelAvailabilityCriterion] = Field(..., min_length=1)
    include_rates: Optional[bool] = True
    include_all_placements: Optional[bool] = True
    include_promo_restricted: Optional[bool] = True
    currency: Optional[constr(min_length=3, max_length=3)] = "KGS"


# --- hotel_availability RESPONSE ---

class PlacementPrice(BaseModel):
    index: int
    price_before_tax: float
    price_after_tax: float
    kind: str
    code: str
    capacity: int
    currency: constr(min_length=3, max_length=3)
    taxes: List[TaxItem] = Field(default_factory=list)
    discount: Optional[DiscountInfo] = None
    age_group: Optional[Union[int, str]] = None


class RoomTypeAvailabilityInfo(BaseModel):
    placements: List[PlacementPrice]
    code: str
    quantity: Optional[int] = Field(None, ge=0)
    limited_inventory_count: Optional[int] = None
    room_type_quota_rph: Optional[str] = None


class RatePlanCancelPenalty(BaseModel):
    code: str
    description: str
    deadline: Optional[Dict[str, Any]] = None
    time_match: Optional[Dict[str, Any]] = None
    guests_count_match: Optional[Dict[str, Any]] = None
    rooms_count_match: Optional[Dict[str, Any]] = None
    periods: Optional[List[Dict[str, Any]]] = None
    penalty: Optional[Dict[str, Any]] = None


class RatePlanCancelPenaltyGroup(BaseModel):
    code: str
    description: str
    free_cancellation: Optional[bool] = None
    show_description: bool = True
    cancel_penalties: List[RatePlanCancelPenalty] = Field(default_factory=list)


class RatePlanAvailabilityInfo(BaseModel):
    code: str
    cancel_penalty_group: RatePlanCancelPenaltyGroup
    promo: bool = False


class GuestPlacementRef(BaseModel):
    index: int


class GuestPlacementInPlacementRates(BaseModel):
    index: int
    kind: str
    code: str


class DailyRate(BaseModel):
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    price_after_tax: float
    currency: constr(min_length=3, max_length=3)
    taxes: List[TaxItem] = Field(default_factory=list)


class PlacementRateInfo(BaseModel):
    room_type_code: str
    rate_plan_code: str
    placement: GuestPlacementInPlacementRates
    rates: List[DailyRate]


class GuestCount(BaseModel):
    placement: GuestPlacementRef
    count: int = Field(..., ge=0)
    age: Optional[int] = Field(None, ge=0)
    age_qualifying_code: Optional[str] = None
    ref: Optional[str] = None


class ServiceInRoomStay(BaseModel):
    rph: int
    applicability_type: Optional[str] = None


class RoomStayAvailability(BaseModel):
    hotel_ref: HotelRef
    guests: List[GuestCount]
    room_types: List[RoomTypeAvailabilityInfo]
    rate_plans: List[RatePlanAvailabilityInfo]
    placement_rates: List[PlacementRateInfo]
    criterion_ref: str
    total: PriceInfo
    services: List[ServiceInRoomStay] = Field(default_factory=list)
    stay_dates: DateRangeStay
    guarantees: List[GuaranteeInfo]
    transfers: List[dict] = Field(default_factory=list)


class ServiceDetailInAvailability(BaseModel):
    code: str
    rph: int
    price: PriceInfo
    inclusive: bool
    quantity: Optional[int] = Field(None, ge=0)
    applicability_type: Optional[str] = None


class RoomTypeQuota(BaseModel):
    rph: str
    quantity: int = Field(..., ge=0)


class AvailabilityResultMessage(BaseModel):
    criterion_ref: Optional[str] = None
    no_room_type_availability_message: Optional[str] = None


class ErrorDetail(BaseModel):
    error_code: str
    message: str
    lang: Optional[str] = None
    info: Optional[str] = None
    location: Optional[str] = None


class WarningDetail(BaseModel):
    error_code: str
    message: str
    lang: Optional[str] = None
    info: Optional[str] = None
    location: Optional[str] = None


class HotelAvailabilityResponse(BaseModel):
    room_stays: List[RoomStayAvailability] = Field(default_factory=list)
    transfers: List[dict] = Field(default_factory=list)
    services: List[ServiceDetailInAvailability] = Field(default_factory=list)
    availability_result: List[AvailabilityResultMessage] = Field(default_factory=list)
    room_type_quotas: List[RoomTypeQuota] = Field(default_factory=list)
    errors: Optional[List[ErrorDetail]] = None
    warnings: Optional[List[WarningDetail]] = None


# --- hotel_reservation_2 REQUEST ---

class RoomTypeReservationPlacement(BaseModel):
    index: int
    kind: str
    code: str


class RoomTypeReservation(BaseModel):
    code: str
    placements: List[RoomTypeReservationPlacement] = Field(..., min_length=1)
    preferences: List[dict] = Field(default_factory=list)


class RatePlanReservation(BaseModel):
    code: str


class GuestCountDetailAPI(BaseModel):
    count: int = Field(..., ge=1)
    age_qualifying_code: str
    placement_index: int
    age: Optional[int] = Field(None, ge=0)


class GuestCountInfoAPI(BaseModel):
    guest_counts: List[GuestCountDetailAPI] = Field(..., min_length=1)
    adults: Optional[int] = None
    children: Optional[int] = None
    index: Optional[Union[int, str]] = None


class GuestInfo(BaseModel):
    placement: GuestPlacementRef
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    citizenship: Optional[str] = None
    sex: Optional[Literal["male", "female"]] = None


class ServiceReservation(BaseModel):
    code: str
    quantity: Optional[int] = Field(None, ge=1)


class GuaranteeReservation(BaseModel):
    code: str
    success_url: AnyHttpUrl
    decline_url: AnyHttpUrl


class CustomerContactPhone(BaseModel):
    phone_number: str


class CustomerContactEmail(BaseModel):
    email_address: str


class CustomerContactInfo(BaseModel):
    phones: List[CustomerContactPhone] = Field(..., min_length=1)
    emails: List[CustomerContactEmail] = Field(..., min_length=1)


class CustomerReservation(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    comment: Optional[str] = None
    confirm_sms: bool = True
    subscribe_email: bool = False
    contact_info: CustomerContactInfo


class RoomStayReservation(BaseModel):
    stay_dates: DateRangeStay
    room_types: List[RoomTypeReservation] = Field(..., min_length=1)
    rate_plans: List[RatePlanReservation] = Field(..., min_length=1)
    guest_count_info: GuestCountInfoAPI
    guests: List[GuestInfo] = Field(..., min_length=1)
    services: List[ServiceReservation] = Field(default_factory=list)


class PointOfSale(BaseModel):
    source_url: AnyHttpUrl
    integration_key: Optional[str] = None


class HotelReservationVerification(BaseModel):
    cancellation_code: str


class HotelReservationRequestItem(BaseModel):
    hotel_ref: HotelRef
    room_stays: List[RoomStayReservation] = Field(..., min_length=1)
    transfers: List[ServiceReservation] = Field(default_factory=list)
    services: List[ServiceReservation] = Field(default_factory=list)
    number: Optional[str] = None
    verification: Optional[HotelReservationVerification] = None
    guarantee: GuaranteeReservation
    customer: CustomerReservation


class HotelReservationRequest(BaseModel):
    language: str = "ru"
    hotel_reservations: List[HotelReservationRequestItem] = Field(..., min_length=1)
    currency: constr(min_length=3, max_length=3) = "KGS"
    include_extra_stay_options: Optional[bool] = False
    include_guarantee_options: Optional[bool] = False
    point_of_sale: Optional[PointOfSale] = None


# --- hotel_reservation_2 RESPONSE ---

class GuestReservationResponse(GuestInfo):
    ref: str
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    count: Optional[int] = None


class RoomTypeReservationPlacementResponse(RoomTypeReservationPlacement):
    rate_plan_code: Union[str, int]
    price_before_tax: float
    price_after_tax: float
    currency: constr(min_length=3, max_length=3)
    capacity: int


class RoomTypeReservationResponse(RoomTypeReservation):
    name: str
    kind: str
    placements: List[RoomTypeReservationPlacementResponse]


class RatePlanReservationResponse(RatePlanReservation):
    name: str
    description: Optional[str] = None
    cancel_penalty_group: RatePlanCancelPenaltyGroup


class ServicePriceDetail(BaseModel):
    price_before_tax: float
    price_after_tax: float
    currency: constr(min_length=3, max_length=3)
    taxes: List[TaxItem] = Field(default_factory=list)


class ServiceReservationResponse(ServiceReservation):
    name: str
    description: Optional[str] = None
    price: ServicePriceDetail
    charge_type: str
    kind: str
    meal_plan_type: Optional[str] = None
    inclusive: bool
    applicability_type: Optional[str] = None


class ExtraStayCharge(BaseModel):
    base_check_in_time: Optional[str] = None
    base_check_out_time: Optional[str] = None


class ExtraStayOptionDetail(BaseModel):
    price: ServicePriceDetail
    date: str
    local_time: str
    forbidden: bool


class ExtraStayChargeOptions(BaseModel):
    early_arrival_rule_description: Optional[str] = None
    late_departure_rule_description: Optional[str] = None
    early_arrival: List[ExtraStayOptionDetail] = Field(default_factory=list)
    late_departure: List[ExtraStayOptionDetail] = Field(default_factory=list)
    base_check_in_time: Optional[str] = None
    base_check_out_time: Optional[str] = None


class RoomStayReservationResponse(RoomStayReservation):
    guests: List[GuestReservationResponse]
    room_types: List[RoomTypeReservationResponse]
    rate_plans: List[RatePlanReservationResponse]
    placement_rates: List[PlacementRateInfo]
    stay_total: PriceInfo
    total: PriceInfo
    services: List[ServiceReservationResponse] = Field(default_factory=list)
    extra_stay_charge: ExtraStayCharge
    extra_stay_charge_options: Optional[ExtraStayChargeOptions] = None
    guest_count_info: GuestCountInfoAPI


class PrepaymentAmountDetail(BaseModel):
    amount: float
    type: str
    currency: constr(min_length=3, max_length=3)


class GuaranteeInfoResponseItem(GuaranteeInfo):
    name: Optional[str] = None
    payment_system_code: Optional[str] = None
    payment_url: Optional[AnyHttpUrl] = None
    texts: Optional[Dict[str, Optional[str]]] = None
    require_prepayment: Optional[bool] = None
    prepayment: Optional[PrepaymentAmountDetail] = None
    payment_system_proxy_code: Optional[str] = None
    name_short: Optional[str] = None
    card_limits: Optional[str] = None


class GuaranteeOverallInfoResponse(BaseModel):
    guarantees: List[GuaranteeInfoResponseItem]
    status: str
    prepayment: Optional[PrepaymentAmountDetail] = None
    payable: Optional[PrepaymentAmountDetail] = None


class CustomerReservationResponse(CustomerReservation):
    pass


class HotelReservationResponseItem(BaseModel):
    number: str
    cancellation_code: str
    status: str
    hotel_ref: HotelRef
    room_stays: List[RoomStayReservationResponse]
    guarantee_info: GuaranteeOverallInfoResponse
    order_url: Optional[AnyHttpUrl] = None
    total: PriceInfo
    create_date: str
    last_modification_date: Optional[str] = None
    customer: CustomerReservationResponse
    language: str
    point_of_sale: Optional[PointOfSale] = None
    services: List[ServiceReservationResponse] = Field(default_factory=list)


class HotelReservationResponse(BaseModel):
    hotel_reservations: Optional[List[HotelReservationResponseItem]] = None
    errors: Optional[List[ErrorDetail]] = None
    warnings: Optional[List[WarningDetail]] = None


# --- cancel_reservation_2 ---

class CancelReservationReason(BaseModel):
    code: str
    text: Optional[str] = None


class CancelReservationVerification(BaseModel):
    cancellation_code: str


class CancelHotelReservationRef(BaseModel):
    number: str
    verification: CancelReservationVerification


class CancelReservationRequestPayload(BaseModel):
    hotel_reservation_refs: List[CancelHotelReservationRef] = Field(..., min_length=1)
    reasons: Optional[List[CancelReservationReason]] = None
    language: str = "ru"


class CancelledHotelReservationItem(BaseModel):
    number: str
    status: str


class CancelReservationResponsePayload(BaseModel):
    hotel_reservations: Optional[List[CancelledHotelReservationItem]] = None
    errors: Optional[List[ErrorDetail]] = None
    warnings: Optional[List[WarningDetail]] = None
