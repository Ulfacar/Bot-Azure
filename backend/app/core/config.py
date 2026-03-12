import sys
import logging

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_SECRETS = {"change-me-in-production", "secret", ""}


class Settings(BaseSettings):
    # Приложение
    app_name: str = "Hotel Bot"
    debug: bool = True

    # База данных
    database_url: str = ""
    database_ssl: bool = False

    # CORS (через запятую)
    cors_origins: str = "http://localhost:3000"

    # Telegram
    telegram_bot_token: str = ""

    # WhatsApp (Meta Cloud API)
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""
    whatsapp_verify_token: str = ""

    # WhatsApp (wappi.pro)
    wappi_api_key: str = ""
    wappi_profile_id: str = ""

    # AI (OpenRouter)
    openrouter_api_key: str = ""
    ai_model: str = "deepseek/deepseek-chat"

    # JWT для админки
    secret_key: str = ""
    access_token_expire_minutes: int = 480

    class Config:
        env_file = ".env"

    def validate_for_startup(self):
        """Проверить критичные переменные при старте."""
        errors = []

        if not self.database_url:
            errors.append("DATABASE_URL не задан")

        if not self.secret_key or self.secret_key in _INSECURE_SECRETS:
            errors.append(
                "SECRET_KEY не задан или небезопасен. "
                "Установите надёжный ключ в .env"
            )

        if errors:
            for err in errors:
                logger.error(f"ОШИБКА КОНФИГУРАЦИИ: {err}")
            print(
                "\n=== ОШИБКА КОНФИГУРАЦИИ ===\n"
                + "\n".join(f"  - {e}" for e in errors)
                + "\n\nИсправьте .env файл и перезапустите.\n",
                file=sys.stderr,
            )
            sys.exit(1)


settings = Settings()
