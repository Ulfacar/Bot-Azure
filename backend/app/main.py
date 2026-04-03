import asyncio
import logging

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.api.routes import api_router
from app.bot.channels.telegram import start_bot, stop_bot
from app.bot.channels.whatsapp import router as whatsapp_router
from app.db.database import async_session
from app.services.conversation import close_stale_conversations
from app.services.followup import send_followups

logging.basicConfig(level=logging.INFO)

# Проверяем конфигурацию до запуска
settings.validate_for_startup()

app = FastAPI(title=settings.app_name)

# Rate limiter ПЕРЕД CORS, чтобы 429 тоже получал CORS хедеры
# (middleware в FastAPI выполняются в обратном порядке добавления)
app.add_middleware(RateLimitMiddleware)

# Разрешаем запросы от фронтенда (админки)
origins = [o.strip() for o in settings.cors_origins.split(",")]
# Всегда разрешаем Vercel
if "https://ton-azure-admin.vercel.app" not in origins:
    origins.append("https://ton-azure-admin.vercel.app")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router)
app.include_router(whatsapp_router)  # WhatsApp webhook


@app.get("/health")
async def health():
    """Health check для Railway / мониторинга."""
    return {"status": "ok"}


# --- Админка (SPA) ---
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if _STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Отдаём index.html для всех не-API маршрутов (SPA fallback)."""
        file = _STATIC_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        return {"status": "ok", "app": settings.app_name}



@app.get("/api/status")
async def status():
    """Статус подключений (Telegram, WhatsApp)."""
    from app.bot.channels.whatsapp import is_whatsapp_configured
    from app.services.wappi_whatsapp import is_wappi_configured
    from app.services.meta_whatsapp import is_whatsapp_configured as is_meta_configured
    from app.bot.channels.telegram import get_bot

    return {
        "telegram": {
            "configured": bool(settings.telegram_bot_token),
            "running": get_bot() is not None,
        },
        "whatsapp": {
            "configured": is_whatsapp_configured(),
            "provider": "wappi.pro" if is_wappi_configured() else ("meta" if is_meta_configured() else "none"),
            "webhook": "/webhook/wappi" if is_wappi_configured() else "/webhook/whatsapp",
        },
    }


async def auto_close_loop():
    """Фоновая задача: закрывать неактивные диалоги каждые 5 минут."""
    logger = logging.getLogger(__name__)
    while True:
        await asyncio.sleep(300)  # 5 минут
        try:
            async with async_session() as session:
                closed = await close_stale_conversations(session, timeout_hours=3)
                if closed:
                    logger.info(f"Автозакрытие: {closed} диалогов")
        except Exception as e:
            logger.error(f"Ошибка автозакрытия: {e}")


async def followup_loop():
    """Фоновая задача: дожим клиентов которые замолчали (каждые 2 минуты)."""
    logger = logging.getLogger(__name__)
    await asyncio.sleep(60)  # Подождать минуту после старта
    while True:
        try:
            async with async_session() as session:
                sent = await send_followups(session)
                if sent:
                    logger.info(f"Дожим: отправлено {sent} напоминаний")
        except Exception as e:
            logger.error(f"Ошибка дожима: {e}")
        await asyncio.sleep(120)  # Каждые 2 минуты


@app.on_event("startup")
async def on_startup():
    """Запуск Telegram бота и автозакрытия в фоне при старте сервера."""
    asyncio.create_task(start_bot())
    asyncio.create_task(auto_close_loop())
    asyncio.create_task(followup_loop())


@app.on_event("shutdown")
async def on_shutdown():
    """Остановка бота при выключении сервера."""
    await stop_bot()
