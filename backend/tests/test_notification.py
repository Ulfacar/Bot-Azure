"""Тесты сервиса уведомлений — состояния менеджеров."""
from app.services.notification import (
    set_operator_replying,
    get_operator_replying,
    clear_operator_replying,
    operator_reply_state,
)


class TestOperatorReplyState:
    def setup_method(self):
        operator_reply_state.clear()

    def test_set_and_get(self):
        set_operator_replying("123456", 42)
        assert get_operator_replying("123456") == 42

    def test_get_none(self):
        assert get_operator_replying("999999") is None

    def test_clear(self):
        set_operator_replying("123456", 42)
        clear_operator_replying("123456")
        assert get_operator_replying("123456") is None

    def test_clear_nonexistent(self):
        clear_operator_replying("999999")  # Не должно падать

    def test_overwrite(self):
        set_operator_replying("123456", 42)
        set_operator_replying("123456", 99)
        assert get_operator_replying("123456") == 99

    def test_multiple_operators(self):
        set_operator_replying("111", 1)
        set_operator_replying("222", 2)
        set_operator_replying("333", 3)
        assert get_operator_replying("111") == 1
        assert get_operator_replying("222") == 2
        assert get_operator_replying("333") == 3
