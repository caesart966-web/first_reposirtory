"""Повтор компаний, по которым Checko отвечал осечкой."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("checko", ROOT / "checko_контакты.py")
checko = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checko)


class TestНужноПовторить(unittest.TestCase):
    def test_сетевая_осечка_повторяется(self):
        # Без этого каждый таймаут молча вычёркивал компанию навсегда:
        # пометка ложится в «Статус (Checko)», а по нему строка считается готовой
        for статус in ("сеть: ReadTimeout", "сеть: ConnectionError",
                       "лимит запросов исчерпан", "HTTP 502", "HTTP 429",
                       "ответ не разобрался"):
            self.assertTrue(checko.нужно_повторить({"Статус (Checko)": статус}),
                            статус)

    def test_окончательный_ответ_не_повторяется(self):
        for статус in ("не найдено в Checko", "действующая", "ликвидирована",
                       "HTTP 403"):
            self.assertFalse(checko.нужно_повторить({"Статус (Checko)": статус}),
                             статус)

    def test_пустой_статус_не_повод(self):
        # Пустая строка — это «ещё не обрабатывали», а не «была осечка»
        self.assertFalse(checko.нужно_повторить({}))
        self.assertFalse(checko.нужно_повторить({"Статус (Checko)": ""}))
        self.assertFalse(checko.нужно_повторить({"Статус (Checko)": "   "}))


class TestИмяПорции(unittest.TestCase):
    def test_имя_рядом_с_общим_файлом(self):
        # Порция должна ложиться рядом с исходным файлом и не затирать его
        from datetime import datetime
        path = Path("C:/mosstroybase/спб_для_checko.xlsx")
        имя = path.with_name(
            f"{path.stem}_прогон_{datetime(2026, 9, 1, 15, 22):%Y-%m-%d_%H%M}{path.suffix}")
        self.assertEqual(имя.name, "спб_для_checko_прогон_2026-09-01_1522.xlsx")
        self.assertEqual(имя.parent, path.parent)
        self.assertNotEqual(имя, path)


if __name__ == "__main__":
    unittest.main()
