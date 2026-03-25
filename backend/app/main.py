import asyncio
import logging

import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.api.routes import api_router
from app.bot.channels.telegram import start_bot, stop_bot
from app.bot.channels.whatsapp import router as whatsapp_router
from app.db.database import async_session
from app.services.conversation import close_stale_conversations

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


@app.get("/")
async def root():
    return {"status": "ok", "app": settings.app_name}


@app.get("/health")
async def health():
    """Health check для Railway / мониторинга."""
    return {"status": "ok"}


@app.post("/api/test-prompt")
async def test_prompt(request: dict = fastapi.Body(...)):
    """Temporary test endpoint — remove after testing."""
    from app.bot.ai.assistant import (
        get_ai_client, SYSTEM_PROMPT, clean_response, needs_operator,
    )
    from app.db.models.models import MessageSender

    messages_input = request.get("messages", [])
    knowledge_hint = request.get("knowledge_hint")

    client = get_ai_client()
    if not client:
        return {"error": "No OpenRouter client"}

    # Build messages array directly (bypass generate_response to avoid SQLAlchemy issues)
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if knowledge_hint:
        api_messages.append({"role": "system", "content": (
            f"=== ПОДСКАЗКА ИЗ БАЗЫ ЗНАНИЙ ===\n{knowledge_hint}\n"
            "Используй если релевантно, иначе игнорируй."
        )})

    for m in messages_input:
        role = "user" if m["role"] == "client" else "assistant"
        api_messages.append({"role": role, "content": m["text"]})

    try:
        response = await client.chat.completions.create(
            model=settings.ai_model,
            max_tokens=800,
            temperature=0.3,
            messages=api_messages,
        )
        raw = response.choices[0].message.content or ""
        return {
            "raw": raw,
            "clean": clean_response(raw),
            "needs_operator": needs_operator(raw),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/status")
async def status():
    """Статус подключений (Telegram, WhatsApp)."""
    from app.services.meta_whatsapp import is_whatsapp_configured
    from app.bot.channels.telegram import get_bot

    return {
        "telegram": {
            "configured": bool(settings.telegram_bot_token),
            "running": get_bot() is not None,
        },
        "whatsapp": {
            "configured": is_whatsapp_configured(),
            "webhook": "/webhook/whatsapp",
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


@app.on_event("startup")
async def on_startup():
    """Запуск Telegram бота и автозакрытия в фоне при старте сервера."""
    asyncio.create_task(start_bot())
    asyncio.create_task(auto_close_loop())


@app.on_event("shutdown")
async def on_shutdown():
    """Остановка бота при выключении сервера."""
    await stop_bot()
