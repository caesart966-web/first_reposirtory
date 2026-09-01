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


if __name__ == "__main__":
    unittest.main()
