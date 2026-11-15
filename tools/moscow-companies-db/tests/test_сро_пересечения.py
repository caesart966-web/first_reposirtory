"""сро_пересечения.py: сколько членов СРО не состоят в проектных и изыскательских СРО."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("пересечения", ROOT / "сро_пересечения.py")
пер = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(пер)

СРО_С = [{"рег_номер": "СРО-С-001-01012009", "id": 1}, {"рег_номер": "СРО-С-002-01012009", "id": 2}]
СРО_ПИ = [{"рег_номер": "СРО-П-001-01012009", "id": 1}, {"рег_номер": "СРО-И-001-01012009", "id": 2}]


def член(n, инн, сро, действ=True):
    return {"id": n, "inn": инн, "sro": {"id": сро},
            "member_status": {"title": "Является членом" if действ else "Исключен"}}


ЧЛЕНЫ_С = [член(1, "7700000001", 1), член(2, "7700000002", 1), член(3, "7700000003", 1),
           член(4, "7700000004", 1, действ=False),                 # исключённый — не считается
           член(5, "7700000001", 2)]
ЧЛЕНЫ_ПИ = [член(11, "7700000001", 1),                             # 0001 — в проектной
            член(12, "7700000002", 2),                             # 0002 — в изыскательской
            член(13, "7700000003", 1, действ=False),               # 0003 — из проектной исключён
            член(14, "7700000005", 1)]


class TestПосчитать(unittest.TestCase):
    def test_числа(self):
        р = пер.посчитать(ЧЛЕНЫ_С, ЧЛЕНЫ_ПИ, СРО_С, СРО_ПИ)
        с1 = р["сро"]["СРО-С-001-01012009"]
        self.assertEqual(с1["действующих"], 3)
        self.assertEqual(с1["не_в_проекте"], 2)          # 0002, 0003 (исключён из проектной = не состоит)
        self.assertEqual(с1["не_в_изысканиях"], 2)       # 0001, 0003
        self.assertEqual(с1["ни_там_ни_там"], 1)         # 0003
        self.assertEqual(р["сро"]["СРО-С-002-01012009"]["не_в_проекте"], 0)
        п = р["сро"]["СРО-П-001-01012009"]
        self.assertEqual((п["действующих"], п["не_в_изысканиях"]), (2, 2))
        и = р["сро"]["СРО-И-001-01012009"]
        self.assertEqual((и["действующих"], и["не_в_проекте"]), (1, 1))
        self.assertEqual((р["инн_в_проектных"], р["инн_в_изыскательских"]), (2, 1))


class TestВыгрузка(unittest.TestCase):
    def test_страницы_и_кэш(self):
        страницы = {1: [член(1, "1", 1), член(2, "2", 1)], 2: [член(2, "2", 1), член(3, "3", 1)]}
        вызовы = []

        def post(path, body=None, попыток=7):
            вызовы.append(body["page"])
            return {"data": {"data": страницы[body["page"]], "count": 3, "countPages": 2}}

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(пер.регион, "post", post), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            члены = пер.все_члены("ноприз", Path(tmp), 2)
            self.assertEqual(пер.регион.BASE, "https://reestr.nopriz.ru/api")
            self.assertEqual(sorted(z["id"] for z in члены), [1, 2, 3])   # повтор на стыке убран
            пер.все_члены("ноприз", Path(tmp), 2)                          # вторая страница — из кэша
        self.assertEqual(вызовы, [1, 2, 1])


class TestПоСРО(unittest.TestCase):
    def test_одна_страница_на_сро_и_кэш(self):
        ответы = {"sro/1/member/list": ([член(1, "1", 1), член(2, "2", 1)], 2),
                  "sro/2/member/list": ([член(3, "3", 2), член(3, "3", 2)], 2)}   # повтор → неполная
        вызовы = []

        def post(path, body=None, попыток=7):
            вызовы.append((path, body["pageCount"]))
            данные, count = ответы[path]
            return {"data": {"data": данные, "count": count, "countPages": 1}}

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(пер.регион, "post", post), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
            члены = пер.члены_по_сро("ноприз", СРО_ПИ, Path(tmp), 2)
            self.assertEqual(sorted(z["id"] for z in члены), [1, 2, 3])
            self.assertIn("уникальных 1 из 2", err.getvalue())
            пер.члены_по_сро("ноприз", СРО_ПИ, Path(tmp), 2)       # полная СРО 1 — из кэша
        self.assertEqual(sorted(вызовы), sorted([("sro/1/member/list", str(пер.ЗА_РАЗ)),
                                                 ("sro/2/member/list", str(пер.ЗА_РАЗ)),
                                                 ("sro/2/member/list", str(пер.ЗА_РАЗ))]))


if __name__ == "__main__":
    unittest.main()
