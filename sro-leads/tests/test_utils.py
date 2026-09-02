from core.utils import dig, inn_checksum_ok, normalize_inn, parse_date


def test_normalize_inn_keeps_string_and_leading_zeros():
    assert normalize_inn("0105012345") == "0105012345"
    assert normalize_inn(" 7814858513 ") == "7814858513"
    assert normalize_inn(7814858513) == "7814858513"
    assert normalize_inn(7814858513.0) == "7814858513"
    assert normalize_inn("7814858513.0") == "7814858513"
    assert normalize_inn("7.814858513E9") == "7814858513"


def test_normalize_inn_pads_lost_leading_zero():
    # Excel превратил 0105012345 в число 105012345
    assert normalize_inn(105012345) == "0105012345"
    assert normalize_inn(12345678901) == "012345678901"


def test_normalize_inn_rejects_garbage():
    assert normalize_inn(None) is None
    assert normalize_inn("") is None
    assert normalize_inn("nan") is None
    assert normalize_inn("12345") is None
    assert normalize_inn("ООО Строитель") is None
    assert normalize_inn(float("nan")) is None


def test_inn_checksum():
    assert inn_checksum_ok("7814858513")
    assert inn_checksum_ok("7813687382")
    assert not inn_checksum_ok("7814858514")


def test_parse_date():
    assert parse_date("2026-01-05") == "2026-01-05"
    assert parse_date("05.01.2026") == "2026-01-05"
    assert parse_date("5.1.26") == "2026-01-05"
    assert parse_date("2026-01-05 10:00:00") == "2026-01-05"
    assert parse_date("мусор") is None
    assert parse_date(None) is None


def test_dig_with_fallbacks():
    obj = {"data": {"data": [1, 2]}, "sro": {"short_description": "СРО А"}}
    assert dig(obj, ["data.items", "data.data"]) == [1, 2]
    assert dig(obj, "sro.short_description") == "СРО А"
    assert dig(obj, "nope.x", default="d") == "d"
