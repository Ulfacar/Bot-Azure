"""
Wappi.pro WhatsApp API клиент.
Документация: https://wappi.pro/docs
"""
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WAPPI_API_BASE = "https://wappi.pro/api/sync/message/send"


def is_wappi_configured() -> bool:
    """Проверить настроен ли wappi.pro."""
    return bool(settings.wappi_api_key and settings.wappi_profile_id)


def _format_phone(phone: str) -> str:
    """Привести номер к формату wappi: только цифры + @c.us."""
    digits = "".join(filter(str.isdigit, phone))
    if not digits.endswith("@c.us"):
        return f"{digits}@c.us"
    return digits


async def send_wappi_message(to: str, text: str) -> bool:
    """
    Отправить текстовое сообщение через wappi.pro API.

    Args:
        to: Номер получателя (например: 996555123456)
        text: Текст сообщения

    Returns:
        True если отправлено успешно
    """
    if not is_wappi_configured():
        logger.error("WhatsApp (wappi.pro) не настроен")
        return False

    recipient = _format_phone(to)

    headers = {
        "Authorization": settings.wappi_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "recipient": recipient,
        "body": text,
    }
    params = {
        "profile_id": settings.wappi_profile_id,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                WAPPI_API_BASE,
                headers=headers,
                json=payload,
                params=params,
            )

            if 200 <= response.status_code < 300:
                data = response.json()
                status = data.get("status", "unknown")
                logger.info(f"WhatsApp (wappi.pro) сообщение отправлено: {status}")
                return True
            else:
                logger.error(
                    f"Ошибка wappi.pro API: {response.status_code} - {response.text}"
                )
                return False

    except Exception as e:
        logger.error(f"Ошибка отправки WhatsApp (wappi.pro): {e}")
        return False


def parse_wappi_webhook(data: dict) -> dict | None:
    """
    Парсинг входящего сообщения из wappi.pro webhook.

    Wappi.pro шлёт POST с JSON:
    {
        "messages": [{
            "id": "...",
            "body": "текст сообщения",
            "from": "996555123456@c.us",
            "fromMe": false,
            "chatId": "996555123456@c.us",
            "type": "chat",
            "senderName": "Имя контакта",
            ...
        }]
    }

    Returns:
        dict с полями: phone, name, text
        или None если это не текстовое сообщение
    """
    try:
        # Статусы доставки и другие служебные события — игнорируем тихо
        if "messages" not in data:
            return None

        messages = data.get("messages", [])
        if not messages:
            return None

        message = messages[0]

        # Пропускаем исходящие сообщения
        if message.get("fromMe", False):
            return None

        # Только текстовые сообщения
        msg_type = message.get("type", "")
        if msg_type not in ("chat", "text"):
            logger.info(f"Пропускаем wappi сообщение типа: {msg_type}")
            return None

        # Извлекаем номер из формата "996555123456@c.us"
        from_raw = message.get("from", "") or message.get("chatId", "")
        phone = from_raw.replace("@c.us", "").replace("@s.whatsapp.net", "")

        if not phone:
            return None

        return {
            "phone": phone,
            "name": message.get("senderName", "") or phone,
            "text": message.get("body", ""),
            "message_id": message.get("id", ""),
        }

    except Exception as e:
        logger.error(f"Ошибка парсинга wappi.pro webhook: {e}")
        return None
