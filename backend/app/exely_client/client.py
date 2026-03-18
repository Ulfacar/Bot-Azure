import httpx
import json
import logging
from typing import Optional, Dict, Any, List, Tuple

from .schemas import (
    HotelAvailabilityRequestParams,
    HotelAvailabilityResponse,
    HotelReservationRequest,
    HotelReservationResponse,
    CancelReservationRequestPayload,
    CancelReservationResponsePayload,
)

logger = logging.getLogger(__name__)


class ExelyApiException(Exception):
    def __init__(
        self,
        status_code: Optional[int] = None,
        error_response: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
    ):
        self.status_code = status_code
        self.error_response = error_response
        super().__init__(message or "Exely API request failed")


def _flatten_availability_params(params: HotelAvailabilityRequestParams) -> List[Tuple[str, str]]:
    flat: List[Tuple[str, Any]] = []

    if params.language is not None:
        flat.append(("language", params.language))
    if params.currency is not None:
        flat.append(("currency", params.currency))
    if params.include_rates is not None:
        flat.append(("include_rates", params.include_rates))
    if params.include_transfers is not None:
        flat.append(("include_transfers", params.include_transfers))
    if params.include_all_placements is not None:
        flat.append(("include_all_placements", params.include_all_placements))
    if params.include_promo_restricted is not None:
        flat.append(("include_promo_restricted", params.include_promo_restricted))

    for i, crit in enumerate(params.criterions):
        flat.append((f"criterions[{i}].ref", crit.ref or "0"))
        for j, hotel in enumerate(crit.hotels):
            flat.append((f"criterions[{i}].hotels[{j}].code", hotel.code))
        flat.append((f"criterions[{i}].dates", crit.dates))
        flat.append((f"criterions[{i}].adults", crit.adults))
        if crit.children is not None:
            flat.append((f"criterions[{i}].children", crit.children))

    result: List[Tuple[str, str]] = []
    for k, v in flat:
        if isinstance(v, bool):
            result.append((k, str(v).lower()))
        else:
            result.append((k, str(v)))
    return result


class ExelyClient:
    """Async клиент для Exely Distribution API."""

    BASE_URL = "https://ibe.hopenapi.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-ApiKey": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[List[Tuple[str, str]]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            response = await self._client.request(
                method, endpoint, params=params, json=json_data
            )
            response.raise_for_status()

            data = response.json()
            return data

        except httpx.HTTPStatusError as e:
            error_body = None
            try:
                error_body = e.response.json()
            except Exception:
                pass
            msg = f"Exely API {e.response.status_code}: {error_body or e.response.text}"
            logger.error(msg)
            raise ExelyApiException(
                status_code=e.response.status_code,
                error_response=error_body,
                message=msg,
            ) from e

        except httpx.RequestError as e:
            msg = f"Exely API network error: {e}"
            logger.error(msg)
            raise ExelyApiException(message=msg) from e

    async def get_hotel_info(self, hotel_code: str, language: str = "ru") -> Dict[str, Any]:
        """Получить информацию об отеле."""
        params = [
            ("language", language),
            ("hotels[0].code", hotel_code),
        ]
        return await self._request(
            "GET",
            "/ChannelDistributionApi/BookingForm/hotel_info",
            params=params,
        )

    async def get_availability(
        self, request_data: HotelAvailabilityRequestParams
    ) -> HotelAvailabilityResponse:
        """Проверить доступность номеров."""
        params = _flatten_availability_params(request_data)
        data = await self._request(
            "GET",
            "/ChannelDistributionApi/BookingForm/hotel_availability",
            params=params,
        )
        return HotelAvailabilityResponse.model_validate(data)

    async def create_reservation(
        self, request_data: HotelReservationRequest
    ) -> HotelReservationResponse:
        """Создать бронирование."""
        payload = request_data.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = await self._request(
            "POST",
            "/ChannelDistributionApi/BookingForm/hotel_reservation_2",
            json_data=payload,
        )

        # Проверяем ошибки в теле ответа (200 OK, но errors в JSON)
        if isinstance(data.get("errors"), list) and data["errors"]:
            first_err = data["errors"][0]
            msg = f"Exely reservation error: {first_err.get('message', 'unknown')}"
            logger.warning(msg)
            raise ExelyApiException(status_code=400, error_response=data, message=msg)

        return HotelReservationResponse.model_validate(data)

    async def cancel_reservation(
        self, request_data: CancelReservationRequestPayload
    ) -> CancelReservationResponsePayload:
        """Отменить бронирование."""
        payload = request_data.model_dump(mode="json", by_alias=True, exclude_none=True)
        data = await self._request(
            "POST",
            "/ChannelDistributionApi/BookingForm/cancel_reservation_2",
            json_data=payload,
        )

        if isinstance(data.get("errors"), list) and data["errors"]:
            first_err = data["errors"][0]
            msg = f"Exely cancel error: {first_err.get('message', 'unknown')}"
            logger.warning(msg)
            raise ExelyApiException(status_code=400, error_response=data, message=msg)

        return CancelReservationResponsePayload.model_validate(data)

    async def close(self):
        await self._client.aclose()
