"""Тесты парсинга webhook сообщений."""
from app.services.meta_whatsapp import parse_webhook_message
from app.services.wappi_whatsapp import parse_wappi_webhook


def test_parse_meta_webhook_text_message():
    data = {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"profile": {"name": "Бектур"}}],
                    "messages": [{
                        "from": "996555123456",
                        "type": "text",
                        "text": {"body": "Хочу забронировать номер"},
                        "id": "msg123",
                    }],
                }
            }]
        }]
    }
    result = parse_webhook_message(data)
    assert result is not None
    assert result["phone"] == "996555123456"
    assert result["name"] == "Бектур"
    assert result["text"] == "Хочу забронировать номер"


def test_parse_meta_webhook_ignores_non_text():
    data = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "996555123456",
                        "type": "image",
                        "id": "msg123",
                    }],
                }
            }]
        }]
    }
    assert parse_webhook_message(data) is None


def test_parse_meta_webhook_empty():
    assert parse_webhook_message({}) is None
    assert parse_webhook_message({"entry": []}) is None


def test_parse_wappi_webhook_text():
    data = {
        "messages": [{
            "id": "msg456",
            "body": "Здравствуйте",
            "from": "996555999888@c.us",
            "fromMe": False,
            "type": "chat",
            "senderName": "Гость",
        }]
    }
    result = parse_wappi_webhook(data)
    assert result is not None
    assert result["phone"] == "996555999888"
    assert result["name"] == "Гость"
    assert result["text"] == "Здравствуйте"


def test_parse_wappi_webhook_ignores_outgoing():
    data = {
        "messages": [{
            "id": "msg789",
            "body": "Ответ",
            "from": "996555999888@c.us",
            "fromMe": True,
            "type": "chat",
        }]
    }
    assert parse_wappi_webhook(data) is None


def test_parse_wappi_webhook_empty():
    assert parse_wappi_webhook({}) is None
    assert parse_wappi_webhook({"messages": []}) is None
