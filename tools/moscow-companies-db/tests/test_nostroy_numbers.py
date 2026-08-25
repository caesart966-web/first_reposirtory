"""Разбор регистрационных номеров СРО в выгрузка_ностроя.py."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ностров", ROOT / "выгрузка_ностроя.py")
ностров = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ностров)


class TestNumberCore(unittest.TestCase):
    def test_full_number_from_registry(self):
        self.assertEqual(ностров.number_core("СРО-С-230-07092010"), "С-230")

    def test_short_number_from_user(self):
        self.assertEqual(ностров.number_core("С-230"), "С-230")
        self.assertEqual(ностров.number_core(" с-230 "), "С-230")

    def test_bare_digits(self):
        self.assertEqual(ностров.number_core("230"), "С-230")
        self.assertEqual(ностров.number_core(230), "С-230")

    def test_latin_c_accepted(self):
        # На клавиатуре латинская C и кириллическая С неразличимы
        self.assertEqual(ностров.number_core("C-230"), "С-230")
        self.assertEqual(ностров.number_core("CPO-C-230-07092010"), "С-230")

    def test_leading_zeros_ignored(self):
        self.assertEqual(ностров.number_core("СРО-С-030-01012010"),
                         ностров.number_core("С-30"))

    def test_empty(self):
        for junk in ("", "   ", None, "—"):
            self.assertEqual(ностров.number_core(junk), "", repr(junk))

    def test_registry_and_user_forms_match(self):
        # Ради этого всё и затевалось: две записи одной СРО должны сойтись
        self.assertEqual(ностров.number_core("СРО-С-306-12102010"),
                         ностров.number_core("С-306"))


class TestRegistrationNumber(unittest.TestCase):
    def test_from_sro_block(self):
        record = {"sro": {"registration_number": "СРО-С-230-07092010"}}
        self.assertEqual(ностров.sro_registration_number(record),
                         "СРО-С-230-07092010")

    def test_from_flat_record(self):
        # Список СРО отдаёт саму организацию, без вложенного блока
        self.assertEqual(
            ностров.sro_registration_number({"registration_number": "СРО-С-306-12102010"}),
            "СРО-С-306-12102010")

    def test_missing(self):
        self.assertEqual(ностров.sro_registration_number({"id": 7}), "")


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, records):
        self._records = records

    def post(self, _url, json=None, timeout=None):
        return _FakeResponse({"data": {"data": self._records, "count": len(self._records)}})

    def get(self, _url, timeout=None):
        return self.post(_url)


class TestIdsByNumber(unittest.TestCase):
    def test_maps_numbers_to_ids(self):
        session = _FakeSession([
            {"id": 247, "registration_number": "СРО-С-230-07092010"},
            {"id": 75, "registration_number": "СРО-С-306-12102010"},
            {"id": 99, "registration_number": "СРО-С-001-01012009"},
        ])
        found = ностров.sro_ids_by_number(session, ["С-230", "C-306"])
        self.assertEqual(found, {"С-230": "247", "С-306": "75"})

    def test_unknown_number_absent(self):
        session = _FakeSession([{"id": 1, "registration_number": "СРО-С-001-01012009"}])
        self.assertEqual(ностров.sro_ids_by_number(session, ["С-230"]), {})


if __name__ == "__main__":
    unittest.main()
