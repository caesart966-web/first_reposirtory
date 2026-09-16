"""Точечная проверка ИНН по реестру НОСТРОЙ."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("ностров", ROOT / "выгрузка_ностроя.py")
ностров = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ностров)


class TestТелоЗапроса(unittest.TestCase):
    def test_формат_как_у_сайта(self):
        # Реестры НОСТРОЯ и НОПРИЗа на одной платформе: pageCount строкой,
        # поиск через searchString. Прежний pageSize реестр молча игнорировал
        self.assertEqual(ностров._тело(2, 500),
                         {"filters": {}, "page": 2, "pageCount": "500",
                          "searchString": "", "sortBy": {}})

    def test_поиск_по_инн(self):
        self.assertEqual(ностров._тело(1, 50, "7708240612")["searchString"],
                         "7708240612")


class TestНормИНН(unittest.TestCase):
    def test_ведущий_ноль(self):
        self.assertEqual(ностров.норм_инн(278147334), "0278147334")
        self.assertEqual(ностров.норм_инн(10103488717), "010103488717")

    def test_обычный(self):
        self.assertEqual(ностров.норм_инн(" 7708240612 "), "7708240612")


def _member(inn, номер, дата, статус="Является членом"):
    return {"inn": inn, "registry_registration_date": дата,
            "member_status": {"title": статус},
            "sro": {"registration_number": номер, "short_description": f"СРО {номер}"}}


class TestЧленстваСтроителя(unittest.TestCase):
    def _payload(self, records):
        return {"data": {"data": records, "count": len(records)}}

    def test_находит_действующее(self):
        найдено = ностров.членства_строителя(self._payload([
            _member("7708240612", "СРО-С-265-10042013", "2019-03-03T00:00:00+03:00")]),
            "7708240612")
        self.assertEqual(найдено[0].strftime("%d.%m.%Y"), "03.03.2019")
        self.assertEqual(найдено[2], "СРО-С-265-10042013")

    def test_берётся_самое_раннее(self):
        найдено = ностров.членства_строителя(self._payload([
            _member("7708240612", "СРО-С-265-10042013", "2022-05-05T00:00:00+03:00"),
            _member("7708240612", "СРО-С-230-07092010", "2018-01-01T00:00:00+03:00")]),
            "7708240612")
        self.assertEqual(найдено[0].strftime("%d.%m.%Y"), "01.01.2018")

    def test_исключённые_не_считаются(self):
        self.assertIsNone(ностров.членства_строителя(self._payload([
            _member("7708240612", "СРО-С-265-10042013", "2018-01-01T00:00:00+03:00",
                    статус="Исключен")]), "7708240612"))

    def test_чужая_компания_отброшена(self):
        # Поиск идёт по строке: ИНН мог встретиться в чужом поле
        self.assertIsNone(ностров.членства_строителя(self._payload([
            _member("7700000000", "СРО-С-265-10042013", "2018-01-01T00:00:00+03:00")]),
            "7708240612"))

    def test_пустой_ответ(self):
        self.assertIsNone(ностров.членства_строителя(self._payload([]), "7708240612"))


if __name__ == "__main__":
    unittest.main()
