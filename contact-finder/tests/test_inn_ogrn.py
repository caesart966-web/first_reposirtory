"""Тесты валидации ИНН/ОГРН по контрольным суммам."""
from validators.inn_ogrn import (
    extract_inn,
    is_valid_inn,
    is_valid_ogrn,
    looks_like_inn,
    validate_inn,
    validate_ogrn,
)


class TestInn10:
    def test_valid_inn_10(self):
        # ИНН Сбербанка — эталонный валидный
        assert is_valid_inn("7707083893")

    def test_valid_inn_10_more(self):
        # ИНН Газпрома
        assert is_valid_inn("7736050003")

    def test_invalid_checksum(self):
        assert not is_valid_inn("7707083894")

    def test_wrong_length(self):
        ok, reason = validate_inn("770708389")
        assert not ok
        assert "10 или 12" in reason

    def test_empty(self):
        ok, reason = validate_inn("")
        assert not ok

    def test_letters_stripped(self):
        assert is_valid_inn("ИНН: 7707083893")

    def test_spaces_and_dashes(self):
        assert is_valid_inn(" 77-07-08-38-93 ")

    def test_all_zeros_rejected(self):
        assert not is_valid_inn("0000000000")

    def test_type_detected(self):
        ok, detail = validate_inn("7707083893")
        assert ok and detail == "юрлицо"


class TestInn12:
    def test_valid_inn_12(self):
        # валидный 12-значный ИНН (ИП)
        assert is_valid_inn("500100732259")

    def test_invalid_inn_12(self):
        assert not is_valid_inn("500100732258")

    def test_type_detected(self):
        ok, detail = validate_inn("500100732259")
        assert ok and detail == "ИП или физлицо"


class TestOgrn:
    def test_valid_ogrn_13(self):
        # ОГРН Сбербанка
        assert is_valid_ogrn("1027700132195")

    def test_invalid_ogrn_13(self):
        assert not is_valid_ogrn("1027700132196")

    def test_valid_ogrnip_15(self):
        assert is_valid_ogrn("304500116000157")

    def test_invalid_ogrnip_15(self):
        assert not is_valid_ogrn("304500116000158")

    def test_wrong_length(self):
        ok, reason = validate_ogrn("12345")
        assert not ok
        assert "13 или 15" in reason


class TestHelpers:
    def test_looks_like_inn(self):
        assert looks_like_inn("7707083893")
        assert not looks_like_inn("привет")
        assert not looks_like_inn("123")

    def test_extract_inn(self):
        assert extract_inn("ИНН 7707083893, ОГРН ...") == "7707083893"
        assert extract_inn("мусор") is None
