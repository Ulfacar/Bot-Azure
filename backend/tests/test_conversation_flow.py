"""Тесты полного флоу бронирования — от первого сообщения до эскалации."""
from unittest.mock import MagicMock

from app.bot.ai.assistant import (
    needs_operator,
    bot_completed,
    extract_category,
    clean_response,
    extract_booking_data,
)
from app.db.models.models import MessageSender


def _msg(text: str, sender: MessageSender = MessageSender.client) -> MagicMock:
    m = MagicMock()
    m.text = text
    m.sender = sender
    return m


class TestNeedsOperator:
    """Тесты детекции запроса менеджера (тег + fallback фразы)."""

    def test_tag(self):
        assert needs_operator("Передаю менеджеру [НУЖЕН_МЕНЕДЖЕР]")

    def test_tag_alone(self):
        assert needs_operator("[НУЖЕН_МЕНЕДЖЕР]")

    def test_no_tag(self):
        assert not needs_operator("Добро пожаловать!")

    # Fallback фразы — когда AI забыл тег
    def test_fallback_peredam(self):
        assert needs_operator("Передам менеджеру для подтверждения")

    def test_fallback_peredayu(self):
        assert needs_operator("Передаю менеджеру ваш запрос")

    def test_fallback_svyazhutsya(self):
        assert needs_operator("Менеджер скоро свяжется с вами")

    def test_fallback_svyazhetsya(self):
        assert needs_operator("Менеджер свяжется с вами в ближайшее время")

    def test_no_false_positive(self):
        assert not needs_operator("Могу ещё чем-то помочь?")
        assert not needs_operator("У нас есть свободные номера")
        assert not needs_operator("Цена 9000 сом за ночь")


class TestBotCompleted:
    def test_tag(self):
        assert bot_completed("Рады были помочь! [ЗАВЕРШЕНО]")

    def test_no_tag(self):
        assert not bot_completed("Чем ещё могу помочь?")


class TestCleanResponse:
    def test_removes_all_tags(self):
        text = "Ответ бота [НУЖЕН_МЕНЕДЖЕР] [ЗАВЕРШЕНО] [КАТЕГОРИЯ:booking]"
        cleaned = clean_response(text)
        assert "[" not in cleaned
        assert "Ответ бота" in cleaned

    def test_empty_after_clean(self):
        assert clean_response("[НУЖЕН_МЕНЕДЖЕР]") == ""

    def test_preserves_normal_text(self):
        assert clean_response("Привет! Как дела?") == "Привет! Как дела?"


class TestExtractCategory:
    def test_all_categories(self):
        assert extract_category("[КАТЕГОРИЯ:booking]") == "booking"
        assert extract_category("[КАТЕГОРИЯ:hotel]") == "hotel"
        assert extract_category("[КАТЕГОРИЯ:service]") == "service"
        assert extract_category("[КАТЕГОРИЯ:general]") == "general"

    def test_invalid_category(self):
        assert extract_category("[КАТЕГОРИЯ:unknown]") is None

    def test_no_category(self):
        assert extract_category("Просто текст") is None

    def test_category_in_middle(self):
        text = "Ответ [КАТЕГОРИЯ:booking] продолжение"
        assert extract_category(text) == "booking"


class TestFullBookingFlow:
    """Имитация полного сценария бронирования через извлечение данных."""

    def test_step_by_step_booking(self):
        """Клиент поэтапно даёт все данные — бот извлекает."""
        dialog = [
            _msg("Хочу забронировать номер"),
            _msg("Какие даты вас интересуют?", MessageSender.bot),
            _msg("С 15 июня по 20 июня, нас будет 2 человека"),
            _msg("Отлично! Подскажите ваше ФИО", MessageSender.bot),
            _msg("Петров Алексей"),
            _msg("И контактный телефон", MessageSender.bot),
            _msg("+996 700 123456"),
        ]

        data = extract_booking_data(dialog)
        assert data.checkin is not None
        assert data.checkout is not None
        assert data.nights == 5
        assert data.adults == 2
        assert data.guest_name == "Петров Алексей"
        assert data.phone is not None
        assert "996" in data.phone

    def test_one_message_booking(self):
        """Клиент даёт все данные в двух сообщениях."""
        dialog = [
            _msg("Забронируйте с 1 июля по 6 июля, 3 человека"),
            _msg("Иванов Сергей, +996 555 987654"),
        ]

        data = extract_booking_data(dialog)
        assert data.checkin is not None
        assert data.checkout is not None
        assert data.nights == 5
        assert data.adults == 3
        assert data.guest_name == "Иванов Сергей"
        assert data.phone is not None

    def test_incomplete_booking(self):
        """Клиент дал только даты — бот должен спросить остальное."""
        dialog = [
            _msg("Хочу на 15 июня — 20 июня"),
        ]

        data = extract_booking_data(dialog)
        assert data.checkin is not None
        assert data.checkout is not None
        assert data.guest_name is None  # Не указано
        assert data.phone is None  # Не указано

    def test_bot_escalation_response(self):
        """AI ответ с тегом эскалации — парсится корректно."""
        ai_response = (
            "Спасибо, Алексей! Все данные собраны. "
            "Передаю менеджеру для подтверждения брони. "
            "[НУЖЕН_МЕНЕДЖЕР] [КАТЕГОРИЯ:booking]"
        )

        assert needs_operator(ai_response)
        assert extract_category(ai_response) == "booking"

        cleaned = clean_response(ai_response)
        assert "[" not in cleaned
        assert "Алексей" in cleaned

    def test_general_question_flow(self):
        """Общий вопрос — бот отвечает сам, помечает [ЗАВЕРШЕНО]."""
        ai_response = (
            "В нашем отеле есть открытый бассейн с подогревом, "
            "он работает бесплатно для всех гостей 😊 [ЗАВЕРШЕНО] [КАТЕГОРИЯ:hotel]"
        )

        assert not needs_operator(ai_response)
        assert bot_completed(ai_response)
        assert extract_category(ai_response) == "hotel"

        cleaned = clean_response(ai_response)
        assert "бассейн" in cleaned
        assert "[" not in cleaned
