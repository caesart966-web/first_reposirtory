"""Строительные компании Москвы: отбор, членство в СРО, выгрузка НОСТРОЙ."""

import importlib.util
import random
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("мс", ROOT / "москва_стройка.py")
мс = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(мс)


def _запись(inn, статус="Является членом", вступил="2019-03-03T00:00:00+03:00",
            вышел=None, сро="СРО Строй", номер="СРО-С-111-01012010", ид=None):
    r = {"inn": inn, "member_status": {"title": статус},
         "registry_registration_date": вступил,
         "sro": {"full_description": сро, "registration_number": номер}}
    if вышел:
        r["suspension_date"] = вышел
    if ид is not None:
        r["id"] = ид
    return r


class TestОКВЭД(unittest.TestCase):
    def test_только_41_42_43(self):
        self.assertEqual(мс.раздел_оквэд("43.21"), "43")
        self.assertEqual(мс.раздел_оквэд("41.20"), "41")
        self.assertIsNone(мс.раздел_оквэд("71.12"))
        self.assertIsNone(мс.раздел_оквэд("46.73"))
        self.assertIsNone(мс.раздел_оквэд(None))

    def test_длинный_код_расшифровывается_по_старшему(self):
        self.assertEqual(мс.название_оквэд("43.21.1"), "Производство электромонтажных работ")
        self.assertEqual(мс.название_оквэд("43.3"), "Работы строительные отделочные")


class TestМосква(unittest.TestCase):
    def test_область_не_москва(self):
        self.assertFalse(мс.москва_по_адресу("141400, Московская обл., г. Химки"))
        self.assertFalse(мс.москва_по_адресу("обл Московская, г Балашиха"))

    def test_москва_и_её_части(self):
        self.assertTrue(мс.москва_по_адресу("город Москва"))
        self.assertTrue(мс.москва_по_адресу("г. Москва, г. Зеленоград, корп. 1"))
        self.assertTrue(мс.москва_по_адресу("108811, г. Москва, поселение Московский"))

    def test_пустой_адрес_ничему_не_противоречит(self):
        self.assertTrue(мс.москва_по_адресу(None))
        self.assertTrue(мс.москва_по_адресу(""))

    def test_другой_регион_назван_явно(self):
        self.assertFalse(мс.москва_по_адресу("Тверская обл, г Тверь"))


class TestСвести(unittest.TestCase):
    def test_нет_записей(self):
        self.assertEqual(мс.свести([])["В СРО"], "Нет")

    def test_действующее_важнее_прошлого(self):
        итог = мс.свести([
            мс.сжать(_запись("7700000001", "Исключен", "2012-01-01", "2016-01-01")),
            мс.сжать(_запись("7700000001", вступил="2018-05-05", сро="СРО Новая")),
        ])
        self.assertEqual(итог["В СРО"], "Да")
        self.assertEqual(итог["СРО"], "СРО Новая")
        self.assertEqual(итог["В СРО с"], "2018-05-05")

    def test_исключена_с_датой_последнего_выхода(self):
        итог = мс.свести([
            мс.сжать(_запись("7700000001", "Исключен", "2012-01-01", "2016-01-01", сро="Старая")),
            мс.сжать(_запись("7700000001", "Исключен", "2017-01-01", "2025-09-10", сро="Поздняя")),
        ])
        self.assertEqual(итог["В СРО"], "Исключена")
        self.assertEqual(итог["СРО"], "Поздняя")
        self.assertEqual(итог["Исключена"], "2025-09-10")

    def test_дата_выхода_из_suspension_date(self):
        # поле подсмотрено в сыром ответе реестра
        r = мс.сжать(_запись("7700000001", "Исключен", вышел="2022-04-19T00:00:00+03:00"))
        self.assertTrue(r["former"])
        self.assertEqual(r["stop"], "2022-04-19")

    def test_ведущий_ноль_в_инн(self):
        self.assertEqual(мс.сжать(_запись(278147334))["inn"], "0278147334")


class _Ответ:
    def __init__(self, code, data=None):
        self.status_code, self._d = code, data

    def json(self):
        return self._d


class TestВыгрузкаНОСТРОЙ(unittest.TestCase):
    """Реестр подменён. Проверяется то, на чём уже обжигались."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        random.seed(3)
        self.реестр = [_запись(f"61{n:08d}", ид=n) for n in range(1, 1001)]
        self.пустая_отдана = False
        self._старый_sleep = мс.time.sleep
        мс.time.sleep = lambda s: None

    def tearDown(self):
        мс.time.sleep = self._старый_sleep

    def _сессия(self, урезать_до=100, пустая_на=4, доля_500=0.1):
        тест = self

        class Сессия:
            def post(self, url, json=None, timeout=None):
                if random.random() < доля_500:
                    return _Ответ(500)
                size, page = min(int(json["pageCount"]), урезать_до), json["page"]
                part = тест.реестр[(page - 1) * size: page * size]
                if page == пустая_на and not тест.пустая_отдана:
                    тест.пустая_отдана = True
                    part = []
                return _Ответ(200, {"data": {"data": part, "count": len(тест.реестр)}})
        return Сессия()

    def _выгрузить(self, **kw):
        сессия = self._сессия(**kw)
        старая, мс.сессия = мс.сессия, lambda: сессия
        try:
            args = мс.main.__globals__["argparse"].Namespace(
                дамп=str(self.dir / "дамп.jsonl"), заново=False, размер=500, пауза=0)
            return мс.cmd_нострой(args)
        finally:
            мс.сессия = старая

    def test_урезанная_страница_и_пустая_посередине(self):
        # Реестр отдаёт 100 вместо 500 — число страниц считается по факту.
        # Пустая страница посреди реестра — сбой, её переспрашивают: так
        # НОПРИЗ однажды «закончился» на 147 тысячах из 212
        self.assertEqual(self._выгрузить(), 0)
        по_инн, уникальных = мс.членства_по_инн(self.dir / "дамп.jsonl")
        self.assertEqual(уникальных, 1000)

    def test_повторный_запуск_не_качает_заново(self):
        self._выгрузить()
        размер = (self.dir / "дамп.jsonl").stat().st_size
        self.assertEqual(self._выгрузить(), 0)
        self.assertEqual((self.dir / "дамп.jsonl").stat().st_size, размер)

    def test_дубли_после_обрыва_схлопываются(self):
        self._выгрузить()
        дамп = self.dir / "дамп.jsonl"
        строки = дамп.read_text(encoding="utf-8").splitlines()
        дамп.write_text("\n".join(строки + строки[:50]) + "\n", encoding="utf-8")
        _, уникальных = мс.членства_по_инн(дамп)
        self.assertEqual(уникальных, 1000)



class TestРеестры(unittest.TestCase):
    def test_нужные_реестры(self):
        нужные = мс.РЕЕСТРЫ_ПО_УМОЛЧАНИЮ
        self.assertTrue(мс.реестр_подходит("СФЕРА изыскатели", нужные))
        self.assertTrue(мс.реестр_подходит("СФЕРА проект", нужные))
        self.assertTrue(мс.реестр_подходит("СФЕРА проектировщиков", нужные))
        self.assertTrue(мс.реестр_подходит("ЯРД Москва", нужные))

    def test_строительные_не_берутся(self):
        # «СИС» в базе — строительная СРО Петербурга; просили «СИС проект»
        нужные = мс.РЕЕСТРЫ_ПО_УМОЛЧАНИЮ
        self.assertIsNone(мс.реестр_подходит("СИС", нужные))
        self.assertIsNone(мс.реестр_подходит("СФЕРА-А", нужные))

    def test_ответ_checko(self):
        # форма ответа — с настоящего ответа Checko /company
        r = мс.разобрать_checko({
            "ОКВЭД": {"Код": "71.12", "Наим": "…"}, "ОКВЭДДоп": [{"Код": "43.21"}],
            "Регион": {"Код": "77", "Наим": "Москва"},
            "ЮрАдрес": {"АдресРФ": "125466, г. Москва, ул. Родионовская, д. 18"},
            "Статус": {"Код": "001", "Наим": "Действует"}})
        self.assertEqual(мс.оценить(r), ("подходит", "43.21", "дополнительный"))

    def test_checko_без_оквэд_не_гадаем(self):
        self.assertIsNone(мс.разобрать_checko({"Регион": {"Код": "77"}}))

    def test_оценка(self):
        self.assertEqual(мс.оценить({"region_code": "77", "okved_main": "41.20"})[0],
                         "подходит")
        self.assertIn("не в Москве", мс.оценить({"region_code": "50",
                                                  "okved_main": "41.20"})[0])
        self.assertIn("нет ОКВЭД 41–43", мс.оценить({"region_code": "77",
                                                      "okved_main": "71.12"})[0])
        self.assertIn("ликвид", мс.оценить({"region_code": "77", "okved_main": "41.20",
                                             "is_active": 0})[0])

if __name__ == "__main__":
    unittest.main()
