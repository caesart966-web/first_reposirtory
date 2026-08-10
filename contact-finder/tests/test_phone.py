"""Тесты нормализации и классификации телефонов."""
from validators.phone import (
    extract_phones,
    format_phone_display,
    normalize_phone,
    phone_type,
)


class TestNormalize:
    def test_plus7(self):
        assert normalize_phone("+7 (495) 123-45-67") == "+74951234567"

    def test_eight(self):
        assert normalize_phone("8 (495) 123-45-67") == "+74951234567"

    def test_bare_seven(self):
        assert normalize_phone("74951234567") == "+74951234567"

    def test_ten_digits(self):
        assert normalize_phone("9261112233") == "+79261112233"

    def test_dots_and_dashes(self):
        assert normalize_phone("8.926.111.22.33") == "+79261112233"

    def test_too_short(self):
        assert normalize_phone("123-45-67") is None

    def test_too_long(self):
        assert normalize_phone("+7 926 111 22 33 44") is None

    def test_foreign_not_russian(self):
        assert normalize_phone("+1 202 555 0134") is None

    def test_empty(self):
        assert normalize_phone("") is None

    def test_zone_zero_invalid(self):
        assert normalize_phone("+7 095 123 45 67") is None


class TestType:
    def test_mobile(self):
        assert phone_type("+79261112233") == "мобильный"

    def test_city(self):
        assert phone_type("+74951234567") == "городской"

    def test_toll_free(self):
        assert phone_type("+78005553535") == "8-800"


class TestExtract:
    def test_from_text(self):
        text = "Звоните: +7 (495) 123-45-67 или 8-926-111-22-33"
        assert extract_phones(text) == ["+74951234567", "+79261112233"]

    def test_inn_not_captured(self):
        # ИНН и ОГРН не должны распознаваться как телефоны
        text = "ИНН 7707083893 ОГРН 1027700132195"
        assert extract_phones(text) == []

    def test_dedup(self):
        text = "тел. 8 (495) 123-45-67, факс +7 495 123-45-67"
        assert extract_phones(text) == ["+74951234567"]

    def test_toll_free_in_text(self):
        assert extract_phones("горячая линия 8 800 555 35 35") == ["+78005553535"]


def test_format_display():
    assert format_phone_display("+74951234567") == "+7 (495) 123-45-67"
