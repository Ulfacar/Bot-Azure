"""Тесты WhatsApp интеграции — форматирование номеров, парсинг webhook."""
from app.services.wappi_whatsapp import _format_phone, parse_wappi_webhook
from app.services.meta_whatsapp import parse_webhook_message


class TestWappiFormatPhone:
    def test_plain_number(self):
        assert _format_phone("996555123456") == "996555123456@c.us"

    def test_plus_prefix(self):
        assert _format_phone("+996555123456") == "996555123456@c.us"

    def test_already_formatted(self):
        result = _format_phone("996555123456@c.us")
        assert result.endswith("@c.us")
        assert "996555123456" in result

    def test_with_spaces(self):
        result = _format_phone("996 555 123 456")
        assert "@c.us" in result


class TestWappiWebhookParsing:
    def test_normal_message(self):
        data = {
            "messages": [{
                "id": "msg1",
                "body": "Здравствуйте, есть номера?",
                "from": "996555123456@c.us",
                "fromMe": False,
                "type": "chat",
                "senderName": "Гость",
            }]
        }
        result = parse_wappi_webhook(data)
        assert result is not None
        assert result["phone"] == "996555123456"
        assert result["name"] == "Гость"
        assert result["text"] == "Здравствуйте, есть номера?"

    def test_outgoing_ignored(self):
        data = {
            "messages": [{
                "id": "msg2",
                "body": "Ответ",
                "from": "996555123456@c.us",
                "fromMe": True,
                "type": "chat",
            }]
        }
        assert parse_wappi_webhook(data) is None

    def test_image_ignored(self):
        data = {
            "messages": [{
                "id": "msg3",
                "body": "",
                "from": "996555123456@c.us",
                "fromMe": False,
                "type": "image",
            }]
        }
        assert parse_wappi_webhook(data) is None

    def test_delivery_status_ignored(self):
        """Статусы доставки не должны парситься как сообщения."""
        data = {"status": "delivered", "messageId": "123"}
        assert parse_wappi_webhook(data) is None

    def test_empty_messages(self):
        assert parse_wappi_webhook({"messages": []}) is None
        assert parse_wappi_webhook({}) is None

    def test_whatsapp_net_format(self):
        data = {
            "messages": [{
                "id": "msg4",
                "body": "Привет",
                "from": "996555123456@s.whatsapp.net",
                "fromMe": False,
                "type": "chat",
                "senderName": "Тест",
            }]
        }
        result = parse_wappi_webhook(data)
        assert result is not None
        assert result["phone"] == "996555123456"


class TestMetaWebhookParsing:
    def test_text_message(self):
        data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"profile": {"name": "Бектур"}}],
                        "messages": [{
                            "from": "996555123456",
                            "type": "text",
                            "text": {"body": "Хочу забронировать"},
                            "id": "msg123",
                        }],
                    }
                }]
            }]
        }
        result = parse_webhook_message(data)
        assert result is not None
        assert result["phone"] == "996555123456"
        assert result["text"] == "Хочу забронировать"
        assert result["name"] == "Бектур"

    def test_non_text_ignored(self):
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

    def test_empty_entry(self):
        assert parse_webhook_message({}) is None
        assert parse_webhook_message({"entry": []}) is None

    def test_no_contacts(self):
        data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "996555123456",
                            "type": "text",
                            "text": {"body": "Привет"},
                            "id": "msg123",
                        }],
                    }
                }]
            }]
        }
        result = parse_webhook_message(data)
        assert result is not None
        assert result["name"] == ""
