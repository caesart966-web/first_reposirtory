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


class TestТелефонИзПочты(unittest.TestCase):
    """Номер, спрятанный в имени почтового ящика."""

    def test_номер_вытащен(self):
        # 89281891734@mail.ru — живой мобильный, который иначе пропал бы
        info = checko.extract({"Контакты": {"Емэйл": "89281891734@mail.ru"}})
        self.assertEqual(info["Телефон из почты"], "+79281891734")
        self.assertEqual(info["Есть телефон"], "да")

    def test_обычная_почта_ничего_не_даёт(self):
        info = checko.extract({"Контакты": {"Емэйл": "info@stroy2024.ru"}})
        self.assertEqual(info["Телефон из почты"], "")
        self.assertEqual(info["Есть телефон"], "нет")

    def test_домен_не_разбирается(self):
        # Цифры после @ — часть домена, а не номер
        info = checko.extract({"Контакты": {"Емэйл": "director@89281891734.ru"}})
        self.assertEqual(info["Телефон из почты"], "")

    def test_дубль_не_добавляется(self):
        info = checko.extract({"Контакты": {"Тел": "+7 928 189-17-34",
                                            "Емэйл": "89281891734@mail.ru"}})
        self.assertEqual(info["Телефоны (Checko)"], "+79281891734")
        self.assertEqual(info["Телефон из почты"], "")
        self.assertEqual(info["Есть телефон"], "да")

    def test_есть_телефон_по_обычному_номеру(self):
        info = checko.extract({"Контакты": {"Тел": "+7 (812) 313-10-04"}})
        self.assertEqual(info["Есть телефон"], "да")

    def test_колонки_объявлены(self):
        for имя in ("Телефон из почты", "Есть телефон"):
            self.assertIn(имя, checko.CONTACT_COLUMNS)


if __name__ == "__main__":
    unittest.main()
