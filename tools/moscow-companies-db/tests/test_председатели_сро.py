"""председатели_сро.py: председатель совета СРО с её сайта — на подставных страницах."""

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("председатели", ROOT / "председатели_сро.py")
пред = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(пред)


def сайт(страницы: dict[str, str]):
    return lambda url: (url, страницы[url]) if url in страницы else None


class TestНайти(unittest.TestCase):
    def т(self, html):
        текст, _ = пред.разобрать(html)
        return пред.найти(текст)

    def test_после_должности(self):
        н = self.т("<h2>Совет Ассоциации</h2><p>Председатель Совета Ассоциации — Иванов Иван Иванович</p>")
        self.assertEqual(н[0], "Иванов Иван Иванович")
        self.assertEqual(н[1], "Председатель совета")
        self.assertIn("Иванов Иван Иванович", н[2])

    def test_перед_должностью(self):
        н = self.т("<tr><td>Петрова Мария Сергеевна</td><td>председатель Совета</td></tr>")
        self.assertEqual(н[0], "Петрова Мария Сергеевна")

    def test_заместитель_не_председатель(self):
        н = self.т("<p>Заместитель председателя Совета Петров Петр Петрович</p>"
                   "<p>Председатель Совета: Сидоров С. С.</p>")
        self.assertEqual(н[0], "Сидоров С. С.")

    def test_чужой_совет(self):
        self.assertIsNone(self.т("<p>Председатель Совета Федерации Матвиенко Валентина Ивановна "
                                 "поздравила строителей</p>"))
        self.assertIsNone(self.т("<p>Председатель Совета НОСТРОЙ Молчанов Антон Николаевич</p>"))

    def test_правление_и_творительный(self):
        self.assertEqual(self.т("<p>Председателем Правления избран Кузнецов Олег Ильич</p>")[0],
                         "Кузнецов Олег Ильич")

    def test_без_имени(self):
        self.assertIsNone(self.т("<p>Председатель Совета Ассоциации проведёт заседание</p>"))


class TestОбход(unittest.TestCase):
    def test_адреса(self):
        self.assertEqual(пред.адреса("https://np-mooss.ru/;  https://mooss.ru/"),
                         ["https://np-mooss.ru/", "https://mooss.ru/"])
        self.assertEqual(пред.адреса("www.npas.ru"), ["http://www.npas.ru"])
        self.assertEqual(пред.адреса(""), [])

    def test_через_ссылку_органы_управления(self):
        страницы = {
            "http://sro.ru": '<a href="/news">Новости</a><a href="/about/organy">Органы управления</a>'
                             '<a href="https://chuzhoy.ru/sovet">Совет у соседей</a>',
            "http://sro.ru/about/organy": "<p>Председатель Совета — Смирнов Алексей Петрович</p>",
            "https://chuzhoy.ru/sovet": "<p>Председатель Совета — Чужой Чужак Чужакович</p>",
        }
        итог = пред.обойти("sro.ru", скачать=сайт(страницы))
        self.assertEqual(итог["Председатель совета"], "Смирнов Алексей Петрович")
        self.assertEqual(итог["Где найдено"], "http://sro.ru/about/organy")
        self.assertEqual(итог[пред.ИТОГ], "найдено")

    def test_не_открылся_и_не_найдено(self):
        self.assertEqual(пред.обойти("dead.ru", скачать=сайт({}))[пред.ИТОГ], "сайт не открылся")
        итог = пред.обойти("sro.ru", скачать=сайт({"http://sro.ru": "<p>Добро пожаловать</p>"}))
        self.assertTrue(итог[пред.ИТОГ].startswith("не найдено"))
        self.assertEqual(пред.обойти("", скачать=сайт({}))[пред.ИТОГ], "сайта нет")


class TestФайл(unittest.TestCase):
    def test_дописывает_и_продолжает(self):
        with tempfile.TemporaryDirectory() as tmp:
            путь = Path(tmp) / "п.xlsx"
            wb = openpyxl.Workbook()
            wb.active.append(пред.ИСХ)
            wb.active.append(["СРО-С-001", "А", "Строительная", "г. Москва", "7700000001", "a.ru"])
            wb.active.append(["СРО-П-002", "Б", "Проектная", "г. Москва", "7700000002", "b.ru"])
            wb.save(путь)
            вызовы = []

            def обойти(сайт):
                вызовы.append(сайт)
                return ({"Председатель совета": "Иванов Иван Иванович", пред.ИТОГ: "найдено"}
                        if сайт == "a.ru" else {пред.ИТОГ: "сайт не открылся"})

            with mock.patch.object(пред, "обойти", обойти), redirect_stdout(io.StringIO()):
                пред.main(["--file", str(путь), "--потоков", "2"])
                пред.main(["--file", str(путь)])                  # второй раз — ничего не обходит
            ws = openpyxl.load_workbook(путь).active
            шапка = [c.value for c in ws[1]]
            строки = [dict(zip(шапка, [c.value for c in r])) for r in ws.iter_rows(min_row=2)]
        self.assertEqual(sorted(вызовы), ["a.ru", "b.ru"])
        self.assertEqual(шапка[:6], пред.ИСХ)
        self.assertEqual(строки[0]["Председатель совета"], "Иванов Иван Иванович")
        self.assertEqual(строки[1][пред.ИТОГ], "сайт не открылся")


if __name__ == "__main__":
    unittest.main()
