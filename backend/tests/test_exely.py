"""Тесты Exely PMS — сезонные цены, форматирование доступности."""
from datetime import date

from app.services.exely import (
    _get_season_price,
    format_availability_for_telegram,
    format_availability_short,
    RoomAvailability,
    ROOM_TYPE_NAMES,
    ROOM_TYPE_TOTAL,
)


class TestSeasonPrices:
    def test_high_season_june(self):
        price = _get_season_price("5064615", date(2026, 6, 15))
        assert price == 9000

    def test_high_season_july(self):
        price = _get_season_price("5064615", date(2026, 7, 15))
        assert price == 9000

    def test_high_season_august(self):
        price = _get_season_price("5064615", date(2026, 8, 15))
        assert price == 9000

    def test_high_season_sep_start(self):
        price = _get_season_price("5064615", date(2026, 9, 10))
        assert price == 9000

    def test_mid_autumn(self):
        price = _get_season_price("5064615", date(2026, 10, 1))
        assert price == 8000

    def test_mid_spring(self):
        price = _get_season_price("5064615", date(2026, 3, 15))
        assert price == 8000

    def test_low_season(self):
        price = _get_season_price("5064615", date(2026, 12, 15))
        assert price == 6000

    def test_triple_prices(self):
        assert _get_season_price("5064616", date(2026, 7, 1)) == 12500
        assert _get_season_price("5064616", date(2026, 12, 1)) == 9000

    def test_family_prices(self):
        assert _get_season_price("5064618", date(2026, 7, 1)) == 15700
        assert _get_season_price("5064618", date(2026, 12, 1)) == 10000

    def test_unknown_type(self):
        assert _get_season_price("9999999", date(2026, 7, 1)) is None

    def test_all_room_types_have_prices(self):
        for type_id in ROOM_TYPE_NAMES:
            price = _get_season_price(type_id, date(2026, 7, 1))
            assert price is not None, f"Нет цены для типа {type_id}"
            assert price > 0


class TestFormatAvailability:
    def _sample_options(self) -> list[RoomAvailability]:
        return [
            RoomAvailability(
                room_type_id="5064615",
                room_type_name="Twin/Double comfort (двухместный)",
                total_rooms=12,
                occupied_rooms=3,
                free_rooms=9,
                max_guests=2,
                price_per_night=9000,
            ),
            RoomAvailability(
                room_type_id="5064616",
                room_type_name="Triple comfort (трёхместный)",
                total_rooms=3,
                occupied_rooms=1,
                free_rooms=2,
                max_guests=3,
                price_per_night=12500,
            ),
        ]

    def test_telegram_format_contains_all_info(self):
        text = format_availability_for_telegram(self._sample_options(), 5)
        assert "Twin/Double" in text
        assert "Triple" in text
        assert "9,000" in text or "9000" in text
        assert "12,500" in text or "12500" in text
        assert "5 ноч" in text
        assert "9 из 12" in text
        assert "2 из 3" in text

    def test_telegram_format_empty(self):
        assert format_availability_for_telegram([], 5) == ""

    def test_short_format(self):
        text = format_availability_short(self._sample_options())
        assert "11" in text  # 9 + 2 свободных
        assert "свободных" in text

    def test_short_format_empty(self):
        assert format_availability_short([]) == ""


class TestRoomTypeConfig:
    def test_all_types_have_names(self):
        for type_id in ROOM_TYPE_TOTAL:
            assert type_id in ROOM_TYPE_NAMES, f"Нет имени для {type_id}"

    def test_total_rooms_is_17(self):
        total = sum(ROOM_TYPE_TOTAL.values())
        assert total == 17, f"Должно быть 17 номеров, а не {total}"
