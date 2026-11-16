"""сро_дополнить.py: заполнить столбцы заказчика по рег. номеру, не трогая остальное."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("дополнить", ROOT / "сро_дополнить.py")
доп = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(доп)


class TestДополнить(unittest.TestCase):
    def test_заголовки(self):
        self.assertEqual(доп.поле("Не состоят \nв проекте"), "не_в_проекте")
        self.assertEqual(доп.поле("Не состоят\nв изиках"), "не_в_изысканиях")
        self.assertEqual(доп.поле("Не состоят в изысканиях"), "не_в_изысканиях")
        self.assertEqual(доп.поле("Председатель совета"), "председатель")
        self.assertIsNone(доп.поле("Проектных СРО\n в регионе"))
        self.assertEqual(доп.поле("Руководитель СРО"), "руководитель")

    def test_руководители_только_в_пустые(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            wb = openpyxl.Workbook()
            wb.active.title = "Руководители"
            wb.active.append(["Рег. номер", "СРО", "Руководитель СРО"])
            wb.active.append(["СРО-И-001", "А", None])
            wb.active.append(["СРО-И-002", "Б", "Заполнено заказчиком"])
            wb.save(tmp / "т.xlsx")
            ч = openpyxl.Workbook()
            ч.active.append(["Наименование", "ИНН", "Рег. номер", "Руководитель", "Должность"])
            ч.active.append(["А", "1", "СРО-И-001", "Иванов Иван Иванович", "Генеральный директор"])
            ч.active.append(["Б", "2", "СРО-И-002", "Петров Пётр Петрович", "Директор"])
            ч.save(tmp / "ч.xlsx")
            with redirect_stdout(io.StringIO()):
                доп.main(["--таблица", str(tmp / "т.xlsx"), "--руководители", str(tmp / "ч.xlsx"),
                          "--out", str(tmp / "о.xlsx")])
            ws = openpyxl.load_workbook(tmp / "о.xlsx")["Руководители"]
        self.assertEqual(ws["C2"].value, "Иванов Иван Иванович, генеральный директор")
        self.assertEqual(ws["C3"].value, "Заполнено заказчиком")

    def test_таблица(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Стройка"
            ws.append(["Рег. номер", "СРО", "Действующих", "Не состоят \nв проекте", "Не состоят\nв изиках",
                       "Руководитель", "Председатель совета"])
            ws.append(["СРО-С-001", "А", 10, None, None, "Иванов", None])
            ws.append(["СРО-С-002", "Б", 5, None, None, "Петров", None])
            ws["A1"].font = Font(bold=True, color="FF0000")
            wp = wb.create_sheet("Изыскания")
            wp.append(["Рег. номер", "СРО", "Не состоят в проекте", "Председатель совета"])
            wp.append(["СРО-И-001", "В", None, None])
            wb.save(tmp / "т.xlsx")
            пред = openpyxl.Workbook()
            пред.active.append(["Рег. номер", "СРО", "Председатель совета", "Где найдено", "Сайт: итог"])
            пред.active.append(["СРО-С-001", "А", "Сидоров Сидор Сидорович", "http://a.ru/sovet", "найдено"])
            пред.active.append(["СРО-И-001", "В", None, None, "сайт не открылся"])
            пред.save(tmp / "п.xlsx")
            (tmp / "x.json").write_text(json.dumps({"сро": {
                "СРО-С-001": {"действующих": 10, "не_в_проекте": 7, "не_в_изысканиях": 9},
                "СРО-И-001": {"действующих": 3, "не_в_проекте": 2}}}), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                доп.main(["--таблица", str(tmp / "т.xlsx"), "--пересечения", str(tmp / "x.json"),
                          "--председатели", str(tmp / "п.xlsx"), "--out", str(tmp / "о.xlsx")])
            о = openpyxl.load_workbook(tmp / "о.xlsx")
        с = [[c.value for c in r] for r in о["Стройка"].iter_rows()]
        self.assertEqual(с[1], ["СРО-С-001", "А", 10, 7, 9, "Иванов", "Сидоров Сидор Сидорович"])
        self.assertEqual(с[2], ["СРО-С-002", "Б", 5, None, None, "Петров", None])   # нет данных — пусто
        self.assertEqual([c.value for c in о["Изыскания"][2]], ["СРО-И-001", "В", 2, None])
        self.assertTrue(о["Стройка"]["A1"].font.bold)                               # оформление на месте
        self.assertEqual(о.sheetnames[-1], "Председатели — где найдено")
        self.assertEqual(о["Председатели — где найдено"]["E2"].value, "http://a.ru/sovet")

    def test_низкая_уверенность_примечанием(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            wb = openpyxl.Workbook()
            wb.active.title = "Стройка"
            wb.active.append(["Рег. номер", "СРО", "Председатель совета"])
            wb.active.append(["СРО-С-001", "А", None])
            wb.active.append(["СРО-С-002", "Б", None])
            wb.save(tmp / "т.xlsx")
            пред = openpyxl.Workbook()
            пред.active.append(["Рег. номер", "СРО", "Председатель совета", "Уверенность", "Сайт: итог"])
            пред.active.append(["СРО-С-001", "А", "Старов С. С.", "низкая", "найдено в документе"])
            пред.active.append(["СРО-С-002", "Б", "Новиков Н. Н.", "высокая", "найдено в документе"])
            пред.save(tmp / "п.xlsx")
            with redirect_stdout(io.StringIO()):
                доп.main(["--таблица", str(tmp / "т.xlsx"), "--председатели", str(tmp / "п.xlsx"),
                          "--out", str(tmp / "о.xlsx")])
            о = openpyxl.load_workbook(tmp / "о.xlsx")["Стройка"]
        self.assertIn("Низкая уверенность", о["C2"].comment.text)
        self.assertIsNone(о["C3"].comment)



if __name__ == "__main__":
    unittest.main()
