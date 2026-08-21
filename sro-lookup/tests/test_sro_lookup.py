"""Тесты поиска СРО. Сеть не нужна."""

from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl

from sro_lookup.reader import read_companies
from sro_lookup.registry import parse_member_payload
from sro_lookup.report import write_report

PAYLOAD = {
    "data": {"data": [{
        "inn": "7813692784",
        "ogrn": "1237800000000",
        "full_description": "Общество с ограниченной ответственностью «ОЛЛИ ИТ»",
        "member_status": {"id": 1, "title": "Является членом СРО"},
        "registry_registration_date": "2023-04-12T00:00:00+03:00",
        "sro": {
            "id": 410,
            "full_description": "Ассоциация «СРО «Балтийский строительный комплекс»",
            "registration_number": "СРО-С-410-16122014",
            "inn": "7825489730",
        },
    }]}
}


class TestParseMember(unittest.TestCase):
    def test_sro_is_extracted(self) -> None:
        info = parse_member_payload(PAYLOAD, "7813692784")
        self.assertTrue(info.found)
        self.assertIn("Балтийский строительный комплекс", info.sro_name)
        self.assertEqual(info.sro_number, "СРО-С-410-16122014")
        self.assertEqual(info.status_text, "Является членом СРО")
        self.assertEqual(info.date_join, date(2023, 4, 12))

    def test_sro_inn_is_not_company_inn(self) -> None:
        """ИНН СРО и ИНН компании нельзя перепутать — это разные лица."""
        info = parse_member_payload(PAYLOAD, "7813692784")
        self.assertEqual(info.sro_inn, "7825489730")
        self.assertNotEqual(info.sro_inn, info.inn)

    def test_other_company_is_not_matched(self) -> None:
        """Запись чужой компании не должна выдаваться за искомую."""
        info = parse_member_payload(PAYLOAD, "7817158012")
        self.assertFalse(info.found)
        self.assertTrue(info.error)


class TestReader(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="sro-test-"))

    def test_columns_are_detected_by_content(self) -> None:
        path = self.tmp / "companies.xlsx"
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.append(["Наименование", "ИНН"])            # шапка — пропускается
        sheet.append(['ООО "ОЛЛИ ИТ"', "7813692784"])
        sheet.append(["7817158012", 'ООО "ФАКТСТРОЙ"'])  # колонки наоборот
        sheet.append(['ООО "ДУБЛЬ"', "7813692784"])      # повтор ИНН
        sheet.append(["мусор", "123"])                    # не ИНН
        book.save(path)

        companies = read_companies(path)
        self.assertEqual([inn for _, inn in companies], ["7813692784", "7817158012"])
        self.assertIn("ОЛЛИ", companies[0][0])
        self.assertIn("ФАКТСТРОЙ", companies[1][0])

    def test_invalid_inn_is_rejected(self) -> None:
        """Десять цифр — ещё не ИНН: контрольная сумма должна сойтись."""
        path = self.tmp / "bad.xlsx"
        book = openpyxl.Workbook()
        book.active.append(["ООО «Ромашка»", "1234567890"])
        book.save(path)
        self.assertEqual(read_companies(path), [])


class TestReport(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="sro-test-"))

    def test_unchecked_is_not_reported_as_absence(self) -> None:
        """Недоступный реестр не должен выглядеть как «не состоит в СРО»."""
        rows = [
            {"name": "ООО «А»", "inn": "7813692784", "sro": "Ассоциация «СРО»",
             "number": "СРО-С-410-16122014", "registry": "НОСТРОЙ",
             "status": "Является членом СРО", "join": date(2023, 4, 12),
             "note": "", "unchecked": False},
            {"name": "ООО «Б»", "inn": "7817158012", "sro": "", "number": "",
             "registry": "", "status": "", "join": None,
             "note": "ПРОВЕРКА НЕ ВЫПОЛНЕНА — нет связи с реестром: НОСТРОЙ, НОПРИЗ",
             "unchecked": True},
        ]
        path = self.tmp / "out.xlsx"
        write_report(rows, path, date(2026, 8, 20))

        sheet = openpyxl.load_workbook(path)["Членство в СРО"]
        self.assertEqual(sheet.cell(1, 3).value, "СРО")
        self.assertEqual(sheet.cell(2, 3).value, "Ассоциация «СРО»")
        note = sheet.cell(3, 8).value
        self.assertIn("НЕ ВЫПОЛНЕНА", note)
        self.assertNotIn("не состоит", note)


if __name__ == "__main__":
    unittest.main(verbosity=2)
