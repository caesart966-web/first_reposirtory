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


class TestTargetSro(unittest.TestCase):
    """Отдельный ответ на вопрос «состоит ли в этой конкретной СРО»."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="sro-test-"))

    def test_abbreviation_does_not_match_inside_words(self) -> None:
        """«ОРС» не должно находиться внутри «ПОМОРСКОГО»."""
        from sro_lookup.target import build_matcher

        matches = build_matcher("ОРС")
        self.assertTrue(matches("Ассоциация «Объединение Ростовских Строителей»"))
        self.assertTrue(matches("СРО Ассоциация ОРС"))
        self.assertFalse(matches("Ассоциация строителей ПОМОРСКОГО края"))
        self.assertFalse(matches("Ассоциация «Балтийский строительный комплекс»"))

    def test_unchecked_never_becomes_no(self) -> None:
        """Реестр не ответил — ответ «не проверено», а не «Нет»."""
        from sro_lookup.target import NO, UNKNOWN, YES, mark_target

        rows = [
            {"inn": "1", "sro": "Ассоциация «Объединение Ростовских Строителей»",
             "number": "", "unchecked": False},
            {"inn": "2", "sro": "Ассоциация «Балтийский комплекс»", "number": "",
             "unchecked": False},
            {"inn": "3", "sro": "", "number": "", "unchecked": True},
        ]
        marked = {row["inn"]: row["target"] for row in mark_target(rows, "ОРС")}
        self.assertEqual(marked["1"], YES)
        self.assertEqual(marked["2"], NO)
        self.assertEqual(marked["3"], UNKNOWN)

    def test_answer_is_same_for_all_rows_of_one_company(self) -> None:
        """Компания в двух СРО занимает две строки — ответ в них одинаковый."""
        from sro_lookup.target import YES, mark_target

        rows = [
            {"inn": "7700000000", "sro": "Ассоциация «Объединение Ростовских Строителей»",
             "number": "", "unchecked": False},
            {"inn": "7700000000", "sro": "Ассоциация проектировщиков «Другая»",
             "number": "", "unchecked": False},
        ]
        self.assertEqual([row["target"] for row in mark_target(rows, "ОРС")], [YES, YES])

    def test_column_is_added_and_filled(self) -> None:
        rows = [{
            "name": "ИП Иванов Иван Иванович", "inn": "616519746524",
            "sro": "Ассоциация «Объединение Ростовских Строителей»",
            "number": "СРО-С-999-01012015", "registry": "НОСТРОЙ",
            "status": "Является членом СРО", "join": date(2022, 3, 1),
            "note": "", "unchecked": False, "target": "Да",
        }]
        path = self.tmp / "target.xlsx"
        write_report(rows, path, date(2026, 8, 21), target_label="ОРС")

        sheet = openpyxl.load_workbook(path)["Членство в СРО"]
        headers = [cell.value for cell in sheet[1]]
        self.assertEqual(headers[2], "Состоит в ОРС")
        self.assertEqual(sheet.cell(2, 3).value, "Да")
        # Колонки после вставленной не должны разъехаться.
        self.assertEqual(headers[3], "СРО")
        self.assertEqual(sheet.cell(2, 4).value, "Ассоциация «Объединение Ростовских Строителей»")


class TestAllNegativeWarning(unittest.TestCase):
    """Поголовно отрицательный результат — повод усомниться, а не вывод."""

    def test_warns_when_nothing_found(self) -> None:
        from sro_lookup.report import all_negative_warning

        rows = [{"inn": str(i), "sro": "", "unchecked": False} for i in range(26)]
        self.assertIn("ни одна компания не найдена", all_negative_warning(rows).lower())

    def test_no_warning_when_at_least_one_found(self) -> None:
        from sro_lookup.report import all_negative_warning

        rows = [{"inn": str(i), "sro": "", "unchecked": False} for i in range(25)]
        rows.append({"inn": "99", "sro": "Ассоциация «СРО»", "unchecked": False})
        self.assertEqual(all_negative_warning(rows), "")

    def test_unchecked_rows_do_not_trigger_warning(self) -> None:
        """Если реестр не отвечал, это уже видно по жёлтым строкам."""
        from sro_lookup.report import all_negative_warning

        rows = [{"inn": str(i), "sro": "", "unchecked": True} for i in range(26)]
        self.assertEqual(all_negative_warning(rows), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
