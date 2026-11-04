"""москва_чистые.py: новые строительные компании Москвы из базы МСП, без СРО."""

import importlib.util
import io
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("чистые", ROOT / "москва_чистые.py")
чистые = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(чистые)
checko = чистые.checko
_spec2 = importlib.util.spec_from_file_location("нострой_для_чистых", ROOT / "выгрузка_ностроя.py")
нострой = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(нострой)


def инн(девять: str) -> str:
    """Дописывает контрольную цифру ИНН юрлица."""
    веса = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    return девять + str(sum(int(ц) * в for ц, в in zip(девять, веса)) % 11 % 10)


A, B, C, D, E, F, G, H, I, J = (инн(f"7701{n:05d}") for n in range(1, 11))


def база(путь: Path, строки: list[dict]) -> None:
    con = sqlite3.connect(путь)
    con.execute("CREATE TABLE companies (inn TEXT PRIMARY KEY, name TEXT, name_short TEXT, kind TEXT, "
                "region_code TEXT, address TEXT, okved_main TEXT, msp_category TEXT, msp_since TEXT, "
                "is_active INTEGER, egrul_status TEXT, sro_member INTEGER)")
    for с in строки:
        полная = {"name": "ООО «Тест»", "name_short": None, "kind": "ЮЛ", "region_code": "77",
                  "address": "г. Москва", "okved_main": "41.20", "msp_category": "микро",
                  "msp_since": "2020-08-10", "is_active": None, "egrul_status": None,
                  "sro_member": None, **с}
        con.execute("INSERT INTO companies VALUES (:inn, :name, :name_short, :kind, :region_code, :address, "
                    ":okved_main, :msp_category, :msp_since, :is_active, :egrul_status, :sro_member)", полная)
    con.commit()
    con.close()


class TestИНН(unittest.TestCase):
    def test_контрольная_цифра(self):
        self.assertTrue(чистые.инн_верный("7707083893"))      # Сбербанк
        self.assertFalse(чистые.инн_верный("7707083894"))
        self.assertFalse(чистые.инн_верный("770708389"))
        self.assertFalse(чистые.инн_верный("770708389312"))   # 12 цифр — ИП, не берём


class TestОтбор(unittest.TestCase):
    def test_кто_не_годится(self):
        строки = [
            {"inn": A, "kind": "ЮЛ", "okved_main": "41.20"},                      # годится
            {"inn": B, "kind": "ИП", "okved_main": "41.20"},                      # ИП
            {"inn": C, "kind": "ЮЛ", "okved_main": "71.12"},                      # не стройка
            {"inn": D, "kind": "ЮЛ", "okved_main": "43.21", "is_active": 0},      # не действует
            {"inn": E, "kind": "ЮЛ", "okved_main": "42.11", "egrul_status": "Находится в стадии ликвидации"},
            {"inn": F, "kind": "ЮЛ", "okved_main": "43.99", "sro_member": 1},     # уже в СРО
            {"inn": G, "kind": "ЮЛ", "okved_main": "41.20"},                      # из прежнего списка
            {"inn": H[:-1] + str((int(H[-1]) + 1) % 10), "kind": "ЮЛ", "okved_main": "41.20"},  # ИНН с ошибкой
        ]
        выбор = чистые.отобрать(строки, {G}, n=100, зерно=1)
        self.assertEqual([r["inn"] for r in выбор], [A])

    def test_сначала_средние_и_малые_потом_старые_микро(self):
        сегодня = date(2026, 11, 4)
        строки = [
            {"inn": A, "msp_category": "микро", "msp_since": "2026-08-10"},   # молодая микро
            {"inn": B, "msp_category": "микро", "msp_since": "2019-08-10"},
            {"inn": C, "msp_category": "малое", "msp_since": "2026-08-10"},
            {"inn": D, "msp_category": "среднее", "msp_since": "2021-08-10"},
        ]
        for r in строки:
            r.update(kind="ЮЛ", okved_main="41.20")
        выбор = чистые.отобрать(строки, set(), n=10, зерно=1, сегодня=сегодня)
        self.assertEqual([r["inn"] for r in выбор], [D, C, B, A])

    def test_n_ограничивает(self):
        строки = [{"inn": x, "kind": "ЮЛ", "okved_main": "41.20"} for x in (A, B, C, D)]
        self.assertEqual(len(чистые.отобрать(строки, set(), n=2, зерно=1)), 2)


class TestКандидаты(unittest.TestCase):
    def test_файл_очереди(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            база(tmp / "б.sqlite3", [{"inn": A, "name_short": "ООО «Альфа»"}, {"inn": B},
                                     {"inn": C, "region_code": "50"}, {"inn": D, "okved_main": "68.20"}])
            прежние = tmp / "прежние.xlsx"
            checko.write_rows(прежние, ["Наименование", "ИНН"], [{"Наименование": "Б", "ИНН": B}])
            out = tmp / "ч.xlsx"
            with redirect_stdout(io.StringIO()):
                код = чистые.main(["кандидаты", "--база", str(tmp / "б.sqlite3"), "--out", str(out),
                                   "--исключить", str(прежние)])
            self.assertEqual(код, 0)
            шапка, строки = checko.read_rows(out)
            self.assertEqual(шапка, чистые.КОЛОНКИ)
            self.assertEqual([(r["Наименование"], r["ИНН"]) for r in строки], [("ООО «Альфа»", A)])

    def test_не_затирает_прогресс(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            база(tmp / "б.sqlite3", [{"inn": A}])
            out = tmp / "ч.xlsx"
            out.write_text("прогресс")
            with redirect_stderr(io.StringIO()):
                код = чистые.main(["кандидаты", "--база", str(tmp / "б.sqlite3"), "--out", str(out),
                                   "--исключить"])
            self.assertEqual(код, 1)
            self.assertEqual(out.read_text(), "прогресс")


def _член(inn, статус="Является членом", дата="2019-03-03T00:00:00+03:00"):
    return {"inn": inn, "registry_registration_date": дата, "member_status": {"title": статус},
            "sro": {"registration_number": "СРО-С-265-10042013", "short_description": "СРО «Тест»"}}


class TestНострой(unittest.TestCase):
    ОТВЕТЫ = {A: [], B: [_член(B)], C: [_член(C, "Исключен")], D: [_член(D, дата=None)],
              E: [_член(F)], F: None, G: [], H: [], I: [], J: []}

    def _прогнать(self, хватит=100):
        def fetch(_session, inn, *a, **k):
            записи = self.ОТВЕТЫ[inn]
            return None if записи is None else {"data": {"data": записи, "count": len(записи)}}

        with tempfile.TemporaryDirectory() as tmp:
            путь = Path(tmp) / "ч.xlsx"
            checko.write_rows(путь, чистые.КОЛОНКИ,
                              [{"Наименование": x, "ИНН": x} for x in (A, B, C, D, E, F, G, H, I, J)])
            with mock.patch.object(нострой, "fetch_by_inn", fetch), \
                    mock.patch.object(нострой, "make_session", lambda: None), \
                    mock.patch.object(чистые, "_модуль", lambda имя, файл: нострой), \
                    mock.patch.object(чистые.time, "sleep", lambda s: None), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                чистые.main(["нострой", "--file", str(путь), "--хватит", str(хватит)])
            _шапка, строки = checko.read_rows(путь)
            return {r["ИНН"]: r for r in строки}

    def test_разбор(self):
        r = self._прогнать()
        self.assertEqual(r[A][чистые.В_НОСТРОЙ], "не состояла")
        self.assertEqual(r[A][checko.НЕ_ПРОБИВАТЬ], "")
        self.assertEqual(r[B][чистые.В_НОСТРОЙ], "состоит")
        self.assertIn("СРО-С-265-10042013", r[B][чистые.СРО_НОСТРОЙ])
        self.assertTrue(r[B][checko.НЕ_ПРОБИВАТЬ])
        self.assertEqual(r[C][чистые.В_НОСТРОЙ], "была")
        self.assertTrue(r[C][checko.НЕ_ПРОБИВАТЬ])
        # запись есть, но без даты — не «чистая» и в Checko не идёт
        self.assertEqual(r[D][чистые.В_НОСТРОЙ], "разобрать вручную")
        self.assertTrue(r[D][checko.НЕ_ПРОБИВАТЬ])
        # поиск вернул чужую компанию — значит, этой в реестре нет
        self.assertEqual(r[E][чистые.В_НОСТРОЙ], "не состояла")
        # реестр не ответил — статус пустой, в Checko не идёт, при повторе спросим снова
        self.assertEqual(r[F][чистые.В_НОСТРОЙ], "")
        self.assertEqual(r[F][checko.НЕ_ПРОБИВАТЬ], чистые.НЕ_ОТВЕТИЛ)
        self.assertEqual(checko.осталось_пробить(list(r.values())),
                         {x for x in (A, E, G, H, I, J)})

    def test_хватит_и_запас(self):
        r = self._прогнать(хватит=2)
        чистых = [x for x in r.values() if x[чистые.В_НОСТРОЙ] == "не состояла"]
        self.assertEqual(len(чистых), 2)
        запас = [x for x in r.values() if x[checko.НЕ_ПРОБИВАТЬ] == чистые.ЗАПАС]
        self.assertTrue(запас)
        # в Checko идут ровно никогда не состоявшие
        self.assertEqual(checko.осталось_пробить(list(r.values())), {x["ИНН"] for x in чистых})


if __name__ == "__main__":
    unittest.main()
