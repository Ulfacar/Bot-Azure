"""Тесты базы знаний — извлечение ключевых слов, нормализация, фильтрация."""
from app.services.knowledge import (
    extract_keywords,
    normalize_word,
    should_auto_save_to_knowledge,
)


class TestExtractKeywords:
    def test_removes_stop_words(self):
        kw = extract_keywords("Как добраться до отеля")
        assert "как" not in kw.split()
        assert "до" not in kw.split()

    def test_removes_punctuation(self):
        kw = extract_keywords("Сколько стоит номер?")
        assert "?" not in kw

    def test_normalizes_words(self):
        kw = extract_keywords("бронирование номеров")
        assert len(kw) > 0

    def test_empty_text(self):
        assert extract_keywords("") == ""

    def test_only_stop_words(self):
        assert extract_keywords("и в на с") == ""

    def test_short_words_removed(self):
        kw = extract_keywords("я ты мы")
        assert kw == ""


class TestNormalizeWord:
    def test_verb_suffix(self):
        # normalize_word убирает типичные русские окончания
        result = normalize_word("забронировать")
        assert len(result) < len("забронировать")

    def test_noun_suffix(self):
        result = normalize_word("бронирование")
        assert len(result) < len("бронирование")

    def test_short_word_unchanged(self):
        assert normalize_word("цена") == "цена"

    def test_adjective_suffix(self):
        result = normalize_word("двухместного")
        assert "двухместн" in result


class TestShouldAutoSave:
    def test_general_question_yes(self):
        assert should_auto_save_to_knowledge("Сколько стоит номер?") is True
        assert should_auto_save_to_knowledge("Где находитесь?") is True
        assert should_auto_save_to_knowledge("Какие есть экскурсии?") is True
        assert should_auto_save_to_knowledge("Есть ли бассейн?") is True
        assert should_auto_save_to_knowledge("Как добраться до отеля?") is True
        assert should_auto_save_to_knowledge("Во сколько завтрак?") is True

    def test_personal_request_no(self):
        assert should_auto_save_to_knowledge("Забронируйте мне номер") is False
        assert should_auto_save_to_knowledge("Запишите на завтра") is False
        assert should_auto_save_to_knowledge("Меня зовут Иван") is False
        assert should_auto_save_to_knowledge("Мой номер +996700123456") is False
        assert should_auto_save_to_knowledge("Нас будет 3 человека") is False

    def test_confirmations_no(self):
        assert should_auto_save_to_knowledge("Спасибо") is False
        assert should_auto_save_to_knowledge("Хорошо") is False
        assert should_auto_save_to_knowledge("Ок") is False
        assert should_auto_save_to_knowledge("Да") is False

    def test_ambiguous_defaults_to_no(self):
        assert should_auto_save_to_knowledge("ааа") is False
        assert should_auto_save_to_knowledge("ну вот") is False
