"""Тесты AI helper функций."""
from app.bot.ai.assistant import (
    needs_operator,
    bot_completed,
    clean_response,
    extract_category,
)


def test_needs_operator_tag():
    assert needs_operator("Подключаю менеджера [НУЖЕН_МЕНЕДЖЕР]")
    assert not needs_operator("Добро пожаловать в наш отель!")


def test_bot_completed_tag():
    assert bot_completed("Спасибо за обращение! [ЗАВЕРШЕНО]")
    assert not bot_completed("Чем могу помочь?")


def test_clean_response_removes_all_tags():
    text = "Ответ [НУЖЕН_МЕНЕДЖЕР] [ЗАВЕРШЕНО] [КАТЕГОРИЯ:booking]"
    cleaned = clean_response(text)
    assert "[НУЖЕН_МЕНЕДЖЕР]" not in cleaned
    assert "[ЗАВЕРШЕНО]" not in cleaned
    assert "[КАТЕГОРИЯ:" not in cleaned
    assert "Ответ" in cleaned


def test_extract_category():
    assert extract_category("Ответ [КАТЕГОРИЯ:booking]") == "booking"
    assert extract_category("Ответ [КАТЕГОРИЯ:hotel]") == "hotel"
    assert extract_category("Ответ [КАТЕГОРИЯ:service]") == "service"
    assert extract_category("Ответ [КАТЕГОРИЯ:general]") == "general"
    assert extract_category("Ответ без категории") is None


def test_clean_response_strips_whitespace():
    assert clean_response("  Привет  ") == "Привет"
    assert clean_response("[НУЖЕН_МЕНЕДЖЕР]") == ""
