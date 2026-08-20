"""Тесты отдельного скрипта нопориз.py (сверка файла с реестром НОПРИЗ)."""

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("нопориз", ROOT / "нопориз.py")
нопориз = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(нопориз)


class TestNormInn(unittest.TestCase):
    def test_leading_zero_restored(self):
        # Excel хранит ИНН числом и съедает ведущий ноль у регионов 01–09
        self.assertEqual(нопориз.norm_inn(816034124), "0816034124")
        self.assertEqual(нопориз.norm_inn(10103488717), "010103488717")

    def test_normal_inn_untouched(self):
        self.assertEqual(нопориз.norm_inn("6164133875"), "6164133875")
        self.assertEqual(нопориз.norm_inn("616413387512"), "616413387512")

    def test_junk_stripped(self):
        self.assertEqual(нопориз.norm_inn(" 6163209497 "), "6163209497")
        self.assertEqual(нопориз.norm_inn("ИНН 6163209497"), "6163209497")
        self.assertEqual(нопориз.norm_inn(None), "")


def _dump_row(inn, kind, started, sro, former="нет"):
    return {"ИНН": inn, "Наименование": "ООО Тест", "ОГРН": "", "СРО": sro,
            "ID СРО": "1", "Вид деятельности": kind, "Дата вступления": started,
            "Статус": "Является членом", "Бывший член": former}


class TestMatch(unittest.TestCase):
    def _run(self, user_rows, dump_rows, user_cols=("Наименование", "ИНН")):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            нопориз.write_rows(tmp / "мой.xlsx", list(user_cols), user_rows, "Мои")
            нопориз.write_rows(tmp / "реестр.xlsx", нопориз.DUMP_COLUMNS,
                               dump_rows, "НОПРИЗ")
            out = tmp / "готово.xlsx"
            code = нопориз.cmd_match(SimpleNamespace(
                file=str(tmp / "мой.xlsx"), nopriz=str(tmp / "реестр.xlsx"),
                out=str(out), inn_column="ИНН"))
            self.assertEqual(code, 0)
            header, rows = нопориз.read_rows(out)
            return header, rows

    def test_two_separate_columns(self):
        header, rows = self._run(
            [{"Наименование": "А", "ИНН": "6164133875"}],
            [_dump_row("6164133875", "проектирование", "15.03.2021", "СРО-П"),
             _dump_row("6164133875", "изыскания", "20.07.2022", "СРО-И")])
        row = rows[0]
        self.assertEqual(row["Проектирование: дата вступления"], "15.03.2021")
        self.assertEqual(row["Проектирование: СРО"], "СРО-П")
        self.assertEqual(row["Изыскания: дата вступления"], "20.07.2022")
        self.assertEqual(row["Изыскания: СРО"], "СРО-И")
        self.assertEqual(row["В НОПРИЗ"], "проектирование и изыскания")
        # Исходные колонки не потерялись и стоят первыми
        self.assertEqual(header[:2], ["Наименование", "ИНН"])

    def test_only_one_kind(self):
        _h, rows = self._run(
            [{"Наименование": "А", "ИНН": "6164133875"}],
            [_dump_row("6164133875", "изыскания", "20.07.2022", "СРО-И")])
        self.assertEqual(rows[0]["Проектирование: дата вступления"], "")
        self.assertEqual(rows[0]["В НОПРИЗ"], "изыскания")

    def test_excluded_membership_ignored(self):
        # Более раннее, но прекращённое членство не должно попасть в отчёт
        _h, rows = self._run(
            [{"Наименование": "А", "ИНН": "6164133875"}],
            [_dump_row("6164133875", "проектирование", "01.01.2015", "старое", "да"),
             _dump_row("6164133875", "проектирование", "05.02.2019", "нынешнее")])
        self.assertEqual(rows[0]["Проектирование: дата вступления"], "05.02.2019")
        self.assertEqual(rows[0]["Проектирование: СРО"], "нынешнее")

    def test_earliest_active_wins(self):
        _h, rows = self._run(
            [{"Наименование": "А", "ИНН": "6164133875"}],
            [_dump_row("6164133875", "проектирование", "15.03.2021", "позже"),
             _dump_row("6164133875", "проектирование", "05.02.2019", "раньше")])
        self.assertEqual(rows[0]["Проектирование: дата вступления"], "05.02.2019")

    def test_lost_leading_zero_still_matches(self):
        # В файле ИНН приехал числом (без нуля), в реестре — полный
        _h, rows = self._run(
            [{"Наименование": "А", "ИНН": "816034124"}],
            [_dump_row("0816034124", "изыскания", "09.09.2023", "СРО-И")])
        self.assertEqual(rows[0]["В НОПРИЗ"], "изыскания")

    def test_missing_inn_marked_separately(self):
        # «нет» означало бы «проверили и не нашли» — это неправда
        _h, rows = self._run([{"Наименование": "А", "ИНН": ""}],
                             [_dump_row("6164133875", "изыскания", "09.09.2023", "С")])
        self.assertEqual(rows[0]["В НОПРИЗ"], "нет ИНН")

    def test_not_found(self):
        _h, rows = self._run([{"Наименование": "А", "ИНН": "6164133875"}],
                             [_dump_row("7701234567", "изыскания", "09.09.2023", "С")])
        self.assertEqual(rows[0]["В НОПРИЗ"], "нет")


if __name__ == "__main__":
    unittest.main()
