"""сро_таблица.py: xlsx по сводке НОСТРОЙ — на настоящей сводке Петербурга."""

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("таблица", ROOT / "сро_таблица.py")
таблица = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(таблица)
СВОДКА = ROOT / "spb_2026_11" / "сводка.json"


class TestТаблица(unittest.TestCase):
    def test_короткое_название(self):
        self.assertEqual(таблица.короткое("СРО А «Объединение строителей СПб»"), "Объединение строителей СПб")
        self.assertEqual(таблица.короткое("Ассоциация «СРО «АЛЬЯНС СТРОИТЕЛЕЙ»"), "СРО «АЛЬЯНС СТРОИТЕЛЕЙ»")
        self.assertEqual(таблица.короткое("Союз строителей"), "Союз строителей")

    def test_петербург(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with redirect_stdout(io.StringIO()):
                таблица.main(["для-checko", "--сводка", str(СВОДКА), "--out", str(tmp / "ч.xlsx")])
            ч = openpyxl.load_workbook(tmp / "ч.xlsx").active
            self.assertEqual([c.value for c in ч[1]], ["Наименование", "ИНН", "Рег. номер"])
            self.assertEqual(ч.max_row, 20)
            # как будто Checko ответил: руководитель одной СРО и одна строка с чужим ИНН
            ч.cell(1, 4, "Руководитель")
            ч.cell(1, 5, "Должность")
            ч.cell(2, 4, "Иванов Иван Иванович")
            ч.cell(2, 5, "Генеральный директор")
            ч.cell(3, 2, "0000000000")
            ч.cell(3, 4, "Петров Пётр Петрович")
            ч.parent.save(tmp / "ч.xlsx")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                таблица.main(["таблица", "--сводка", str(СВОДКА), "--out", str(tmp / "т.xlsx"),
                              "--руководители", str(tmp / "ч.xlsx")])
            wb = openpyxl.load_workbook(tmp / "т.xlsx")
        self.assertEqual(wb.sheetnames, ["Сводная", "Вступления по месяцам", "Исключения по месяцам"])
        ws = wb["Сводная"]
        self.assertEqual([c.value for c in ws[1]], таблица.ШАПКА)
        self.assertEqual(ws.freeze_panes, "C2")
        первая = [c.value for c in ws[2]]
        self.assertEqual(первая[:5], ["СРО-С-003-22042009", "Объединение строителей СПб", 2562, 792, 1770])
        self.assertEqual(первая[-1], "Иванов Иван Иванович, генеральный директор")
        self.assertFalse([c.value for c in ws[3]][-1])               # ИНН не сошёлся — не вписан
        итог = [c.value for c in ws[21]]
        self.assertEqual((итог[1], итог[2]), ("Итого по 19 СРО", "=SUM(C2:C20)"))
        мес = wb["Вступления по месяцам"]
        self.assertEqual([c.value for c in мес[1]][2], "2023-01")


if __name__ == "__main__":
    unittest.main()
