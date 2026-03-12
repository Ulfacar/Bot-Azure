"""
Простой in-memory rate limiter для API.
Ограничивает количество запросов по IP-адресу.
"""
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# IP -> список timestamp'ов запросов
_requests: dict[str, list[float]] = defaultdict(list)

# Настройки
RATE_LIMIT = 60  # запросов
RATE_WINDOW = 60  # секунд


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропускаем health check и статику
        path = request.url.path
        if path in ("/health", "/", "/docs", "/openapi.json"):
            return await call_next(request)

        # Пропускаем вебхуки от Telegram/WhatsApp (доверенные сервисы)
        if path.startswith("/webhook/"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Чистим старые записи
        _requests[client_ip] = [
            t for t in _requests[client_ip] if now - t < RATE_WINDOW
        ]

        if len(_requests[client_ip]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Слишком много запросов. Попробуйте позже."},
            )

        _requests[client_ip].append(now)
        return await call_next(request)
