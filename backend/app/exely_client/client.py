"""Клиент для Exely PMS API (connect.hopenapi.com)."""

import httpx
import logging
from typing import Optional, Dict, Any, List

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
        super().__init__(message or "Exely PMS API request failed")


class ExelyPMSClient:
    """Async клиент для Exely PMS API."""

    BASE_URL = "https://connect.hopenapi.com/api/exelypms/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Any:
        try:
            response = await self._client.request(method, endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_body = None
            try:
                error_body = e.response.json()
            except Exception:
                pass
            msg = f"Exely PMS {e.response.status_code}: {error_body or e.response.text}"
            logger.error(msg)
            raise ExelyApiException(
                status_code=e.response.status_code,
                error_response=error_body,
                message=msg,
            ) from e
        except httpx.RequestError as e:
            msg = f"Exely PMS network error: {e}"
            logger.error(msg)
            raise ExelyApiException(message=msg) from e

    async def get_rooms(self) -> List[Dict[str, Any]]:
        """Получить все номера отеля.

        Возвращает список: [{"id": "...", "name": "...", "roomTypeId": "..."}, ...]
        """
        return await self._request("GET", "/rooms")

    async def search_bookings(
        self,
        state: str = "Active",
        affects_period_from: Optional[str] = None,
        affects_period_to: Optional[str] = None,
    ) -> List[str]:
        """Поиск бронирований по периоду.

        affects_period_from/to — формат yyyy-MM-ddTHH:mm
        Возвращает список номеров бронирований.
        """
        params: Dict[str, str] = {"state": state}
        if affects_period_from:
            params["affectsPeriodFrom"] = affects_period_from
        if affects_period_to:
            params["affectsPeriodTo"] = affects_period_to

        data = await self._request("GET", "/bookings", params=params)
        return data.get("bookingNumbers", [])

    async def get_booking(self, booking_number: str, language: str = "ru") -> Dict[str, Any]:
        """Получить детали бронирования."""
        return await self._request(
            "GET",
            f"/bookings/{booking_number}",
            params={"language": language},
        )

    async def close(self):
        await self._client.aclose()
