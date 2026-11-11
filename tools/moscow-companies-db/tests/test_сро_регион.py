"""сро_регион.py: сводка по СРО одного города — на подставных ответах реестра."""

import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("регион", ROOT / "сро_регион.py")
регион = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(регион)

СРО = [
    {"id": 10, "registration_number": "СРО-С-001-01012009", "region_name": "Москва", "state": "enabled"},
    {"id": 11, "registration_number": "СРО-С-002-01012009", "region_name": "г. Москва", "state": "enabled"},
    {"id": 12, "registration_number": "СРО-С-003-01012009", "region_name": "Санкт-Петербург", "state": "enabled"},
    {"id": 13, "registration_number": "СРО-С-004-01012009", "region_name": "Московская область", "state": "enabled"},
]


def член(mid, inn, вступ, статус="Является членом", номер="1"):
    return {"id": mid, "inn": inn, "registration_number": номер,
            "registry_registration_date": f"{вступ}T00:00:00+03:00",
            "member_status": {"title": статус},
            "last_updated_at_date_time_string": "01.01.2026 10:00:00"}


ЧЛЕНЫ = {
    10: [член(1, "7700000001", "2023-03-10"),
         член(2, "7700000002", "2024-05-01", "Исключен", "2"),      # дата в архиве
         член(3, "7700000003", "2025-01-20", "Исключен", "3")],     # даты в архиве нет → карточка
    11: [член(4, "7700000004", "2026-02-02")],
}
АРХИВ = {10: [("1", "7700000001", "10.03.2023", None),
              ("2", "7700000002", "01.05.2024", "14.02.2025"),
              ("3", "7700000003", "20.01.2025", None)],
         11: [("1", "7700000004", "02.02.2026", None)]}


def архив_zip(строки) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Реестр членов"])
    ws.append(["", "N п/п", "Регистрационный номер в реестре СРО", "Дата регистрации в реестре СРО",
               "Дата прекращения членства", "ИНН"])
    for i, (номер, инн, вступ, прекр) in enumerate(строки, 1):
        ws.append(["", i, номер, вступ, прекр, инн])
        ws.append(["", None, None, None, None, None])           # строка-продолжение
    xlsx = io.BytesIO()
    wb.save(xlsx)
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("register-1-500.xlsx", xlsx.getvalue())
    return z.getvalue()


def post(path, body=None, попыток=7):
    if path == "sro/list":
        return {"data": {"data": СРО, "count": len(СРО), "countPages": 1}}
    части = path.split("/")
    if части[0] == "sro" and len(части) == 2:
        return {"data": {"inn": f"77{части[1]}", "short_description": f"СРО {части[1]}"}}
    if части[0] == "sro" and части[2] == "member":
        записи = ЧЛЕНЫ.get(int(части[1]), [])
        return {"data": {"data": записи, "count": len(записи), "countPages": 1}}
    if части[0] == "member":
        return {"data": {"suspension_date": "2025-09-05T00:00:00+03:00"}}
    raise AssertionError(path)


class TestРегион(unittest.TestCase):
    def test_москва(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "сводка.json"
            with mock.patch.object(регион, "post", post), \
                    mock.patch.object(регион, "скачать_архив",
                                      lambda sid, путь: путь.write_bytes(архив_zip(АРХИВ[sid]))), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                регион.main(["--регион", "г. Москва", "--кэш", tmp, "--out", str(out), "--потоков", "2"])
            d = json.loads(out.read_text(encoding="utf-8"))
        номера = [x["рег_номер"] for x in d["сро"]]
        # «Москва» и «г. Москва» — один город; Московская область и Петербург — нет
        self.assertEqual(номера, ["СРО-С-001-01012009", "СРО-С-002-01012009"])
        x = d["сро"][0]
        self.assertEqual((x["всего_записей"], x["действующих"], x["исключённых_всего"]), (3, 1, 2))
        self.assertEqual((x["исключено_2025"], x["без_даты_искл"]), (2, 0))
        self.assertEqual(x["исключения_по_месяцам"]["2025-02"], 1)     # из архива
        self.assertEqual(x["исключения_по_месяцам"]["2025-09"], 1)     # из карточки
        self.assertEqual(x["вступления_по_месяцам"]["2023-03"], 1)
        self.assertEqual(x["инн"], "7710")

    def test_все_через_ноприз_и_сбой_одной(self):
        адреса = []

        def post_с_ошибкой(path, body=None, попыток=7):
            адреса.append(регион.BASE)
            if path == "sro/12":                       # одна СРО не отвечает
                raise RuntimeError("HTTP 503")
            if path.startswith("sro/") and path.split("/")[1] in ("12", "13") and "member" in path:
                return {"data": {"data": [], "count": 0, "countPages": 1}}
            return post(path, body, попыток)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "сводка.json"
            with mock.patch.object(регион, "post", post_с_ошибкой), \
                    mock.patch.object(регион, "скачать_архив",
                                      lambda sid, путь: путь.write_bytes(архив_zip(АРХИВ.get(sid, [])))), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                регион.main(["--реестр", "ноприз", "--все", "--кэш", tmp, "--out", str(out)])
            d = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(all(a == "https://reestr.nopriz.ru/api" for a in адреса))
        self.assertEqual(d["реестр"], "ноприз")
        по = {x["рег_номер"]: x for x in d["сро"]}
        self.assertEqual(len(по), 4)                                     # все СРО, без фильтра по городу
        self.assertIn("503", по["СРО-С-003-01012009"]["ошибка"])          # сбой одной — не падение всех
        self.assertEqual(по["СРО-С-003-01012009"]["карточка"]["город"], "Санкт-Петербург")
        self.assertEqual(по["СРО-С-001-01012009"]["действующих"], 1)
        self.assertEqual(по["СРО-С-004-01012009"]["всего_записей"], 0)

    def test_нужен_регион_или_номера(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            регион.main(["--out", "x.json"])


if __name__ == "__main__":
    unittest.main()


class ГородНоприз(unittest.TestCase):
    """У НОПРИЗ в sro/list нет region_name — город берётся из city."""

    def test_город_из_city(self):
        x = {"registration_number": "СРО-П-005-21052009", "city": "Белгород",
             "federal_district": {"id": 3, "title": "Центральный ФО"}}
        self.assertEqual(регион.город_сро(x), "Белгород")
        self.assertEqual(регион.место_сро(x)["федеральный_округ"], "Центральный ФО")
        self.assertIsNone(регион.место_сро(x)["регион_реестра"])
        self.assertEqual(регион.выбрать_сро({"СРО-П-005-21052009": x}, "г. Белгород", []),
                         ["СРО-П-005-21052009"])

    def test_нострой_region_name_главнее(self):
        x = {"region_name": "Алтайский край", "city": "Барнаул"}
        self.assertEqual(регион.город_сро(x), "Алтайский край")
        self.assertEqual(регион.место_сро(x)["город_реестра"], "Барнаул")
