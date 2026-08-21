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


class TestActivityKind(unittest.TestCase):
    def test_by_sro_registration_number(self):
        # Номер СРО кодирует вид: СРО-П-… проектные, СРО-И-… изыскательские
        self.assertEqual(
            нопориз.activity_kind({"sro": {"registration_number": "СРО-П-147-09032010"}}),
            "проектирование")
        self.assertEqual(
            нопориз.activity_kind({"sro": {"registration_number": "СРО-И-032-2010"}}),
            "изыскания")

    def test_number_beats_names(self):
        # Название СРО говорит «изыскателей», номер — проектная: верим номеру
        record = {"sro": {"registration_number": "СРО-П-147-09032010",
                          "full_description": "Союз изыскателей"}}
        self.assertEqual(нопориз.activity_kind(record), "проектирование")

    def test_company_name_does_not_leak(self):
        # ООО «Проектстрой» в изыскательской СРО — это изыскания, не проектирование
        record = {"short_description": 'ООО "Проектстрой"',
                  "sro": {"short_description": "Ассоциация изыскателей"}}
        self.assertEqual(нопориз.activity_kind(record), "изыскания")

    def test_falls_back_to_sro_name(self):
        self.assertEqual(
            нопориз.activity_kind({"sro": {"short_description": "Ассоциация проектировщиков"}}),
            "проектирование")

    def test_unknown_stays_empty(self):
        self.assertEqual(нопориз.activity_kind({"sro": {"short_description": "Союз"}}), "")


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeSession:
    """Реестр, который слушается только одного имени параметра."""

    def __init__(self, honours: str | None, default_size: int = 20,
                 paginates: bool = True):
        self.honours, self.default_size, self.paginates = honours, default_size, paginates
        self.calls = []

    def post(self, _url, json=None, timeout=None):
        self.calls.append(dict(json))
        size = json.get(self.honours, self.default_size) if self.honours else self.default_size
        page = json["page"] if self.paginates else 1
        start = (page - 1) * size
        data = [{"id": start + i, "inn": f"{start + i:010d}"} for i in range(size)]
        return _FakeResponse({"data": {"data": data, "count": 1000}})


class TestProbePageSize(unittest.TestCase):
    def test_finds_working_key(self):
        session = _FakeSession(honours="limit")
        key, size = нопориз.probe_page_size(session, 100)
        self.assertEqual((key, size), ("limit", 100))

    def test_falls_back_when_nothing_works(self):
        session = _FakeSession(honours=None)
        key, size = нопориз.probe_page_size(session, 100)
        self.assertEqual((key, size), ("pageSize", 20))

    def test_rejects_key_that_ignores_page(self):
        # Размер слушается, но вторая страница повторяет первую (limit/offset):
        # такой ключ дал бы десять тысяч копий первой страницы
        session = _FakeSession(honours="limit", paginates=False)
        key, size = нопориз.probe_page_size(session, 100)
        self.assertEqual(key, "pageSize")


class TestDumpColumns(unittest.TestCase):
    def test_registration_number_stored(self):
        # Без него вид деятельности не пересчитать, не выкачивая реестр заново
        self.assertIn("Рег. номер СРО", нопориз.DUMP_COLUMNS)


class TestReclassify(unittest.TestCase):
    """Починка вида деятельности в уже скачанной выгрузке, без повторной качки."""

    OLD_COLUMNS = ["ИНН", "Наименование", "ОГРН", "СРО", "ID СРО",
                   "Вид деятельности", "Дата вступления", "Статус", "Бывший член"]

    def _dump(self, tmp, rows, columns=None):
        path = tmp / "реестр.xlsx"
        нопориз.write_rows(path, list(columns or self.OLD_COLUMNS), rows, "НОПРИЗ")
        return path

    def test_company_name_leak_repaired(self):
        # Старая выгрузка: вид определялся по всем строкам записи, поэтому
        # ООО «Проектстрой» в изыскательской СРО получило оба вида
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = self._dump(tmp, [{"ИНН": "6164133875", "Наименование": "ООО Проектстрой",
                                    "СРО": "Ассоциация изыскателей", "ID СРО": "7",
                                    "Вид деятельности": "проектирование, изыскания"}])
            out = tmp / "исправлено.xlsx"
            code = нопориз.cmd_reclassify(SimpleNamespace(
                nopriz=str(src), справочник=None, out=str(out)))
            self.assertEqual(code, 0)
            _h, rows = нопориз.read_rows(out)
            self.assertEqual(rows[0]["Вид деятельности"], "изыскания")

    def test_registration_number_wins_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = self._dump(tmp, [{"ИНН": "6164133875", "СРО": "Союз изыскателей",
                                    "ID СРО": "7", "Рег. номер СРО": "СРО-П-147-09032010",
                                    "Вид деятельности": ""}],
                             columns=нопориз.DUMP_COLUMNS)
            out = tmp / "исправлено.xlsx"
            нопориз.cmd_reclassify(SimpleNamespace(nopriz=str(src), справочник=None,
                                                   out=str(out)))
            _h, rows = нопориз.read_rows(out)
            self.assertEqual(rows[0]["Вид деятельности"], "проектирование")

    def test_guide_fills_unrecognised_sro(self):
        # У СРО нейтральное название — вид проставляется руками через справочник
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = self._dump(tmp, [{"ИНН": "6164133875", "СРО": "Союз «Гарант»",
                                    "ID СРО": "42", "Вид деятельности": ""}])
            guide = tmp / "виды.xlsx"
            нопориз.write_rows(guide, нопориз.GUIDE_COLUMNS,
                               [{"ID СРО": "42", "СРО": "Союз «Гарант»", "Записей": "5",
                                 "Вид деятельности": "изыскания"}], "СРО")
            out = tmp / "исправлено.xlsx"
            нопориз.cmd_reclassify(SimpleNamespace(nopriz=str(src),
                                                   справочник=str(guide), out=str(out)))
            _h, rows = нопориз.read_rows(out)
            self.assertEqual(rows[0]["Вид деятельности"], "изыскания")

    def test_columns_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = self._dump(tmp, [{"ИНН": "6164133875", "СРО": "Ассоциация изыскателей",
                                    "ID СРО": "7", "Вид деятельности": "",
                                    "Дата вступления": "01.02.2020"}])
            out = tmp / "исправлено.xlsx"
            нопориз.cmd_reclassify(SimpleNamespace(nopriz=str(src), справочник=None,
                                                   out=str(out)))
            header, rows = нопориз.read_rows(out)
            self.assertEqual(header, self.OLD_COLUMNS)
            self.assertEqual(rows[0]["Дата вступления"], "01.02.2020")


class TestKindsReport(unittest.TestCase):
    def test_groups_by_sro_and_marks_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            src = tmp / "реестр.xlsx"
            нопориз.write_rows(src, TestReclassify.OLD_COLUMNS, [
                {"ИНН": "1", "СРО": "Ассоциация проектировщиков", "ID СРО": "1"},
                {"ИНН": "2", "СРО": "Ассоциация проектировщиков", "ID СРО": "1"},
                {"ИНН": "3", "СРО": "Союз «Гарант»", "ID СРО": "42"},
            ], "НОПРИЗ")
            out = tmp / "виды.xlsx"
            code = нопориз.cmd_kinds(SimpleNamespace(nopriz=str(src), out=str(out)))
            self.assertEqual(code, 0)
            _h, rows = нопориз.read_rows(out)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["Записей"], "2")            # крупные сверху
            self.assertEqual(rows[0]["Вид деятельности"], "проектирование")
            self.assertEqual(rows[1]["Вид деятельности"], "")    # заполнить руками


class TestCliArgs(unittest.TestCase):
    def test_cyrillic_flag_parses(self):
        parser_ok = нопориз.main(["пересчитать", "--nopriz", "нет.xlsx",
                                  "--справочник", "нет.xlsx"])
        self.assertEqual(parser_ok, 1)   # файлов нет, но разбор аргументов прошёл


if __name__ == "__main__":
    unittest.main()
