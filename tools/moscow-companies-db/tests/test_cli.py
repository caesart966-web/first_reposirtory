import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from mosstroybase.cli import main, todays_checko_inns
from mosstroybase.db import CompanyDB

SAMPLE = Path(__file__).parent / "data" / "sample_rsmp.xml"


class TestCliEndToEnd(unittest.TestCase):
    def test_build_and_export(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "base.sqlite3")
            csv_path = str(Path(tmp) / "out.csv")

            rc = main(["--db", db_path, "build", "--rsmp-file", str(SAMPLE)])
            self.assertEqual(rc, 0)

            rc = main(["--db", db_path, "export", "--csv", csv_path])
            self.assertEqual(rc, 0)

            with open(csv_path, encoding="utf-8-sig") as fh:
                rows = list(csv.reader(fh, delimiter=";"))
            self.assertEqual(rows[0][0], "ИНН")
            inns = {row[0] for row in rows[1:]}
            # Проектировщик 7709876543 (71.12.45) в дефолтный набор не входит
            self.assertEqual(inns, {"7701234567", "7706666666"})

    def test_import_inn(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "base.sqlite3")
            inns_file = Path(tmp) / "inns.txt"
            inns_file.write_text("7736520080\nне-инн\n5036045205\n\n", encoding="utf-8")
            rc = main(["--db", db_path, "import-inn", "--file", str(inns_file)])
            self.assertEqual(rc, 0)
            csv_path = str(Path(tmp) / "out.csv")
            main(["--db", db_path, "export", "--csv", csv_path])
            with open(csv_path, encoding="utf-8-sig") as fh:
                rows = list(csv.reader(fh, delimiter=";"))
            self.assertEqual({r[0] for r in rows[1:]}, {"7736520080", "5036045205"})


class TestEnrichSroFromFile(unittest.TestCase):
    def test_checks_exactly_the_file_inns_adding_missing_ones(self):
        # "1" уже в базе (из другого источника), "2" — новый, только из файла;
        # оба должны быть проверены, а компании из базы вне файла — нет
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "base.sqlite3")
            with CompanyDB(db_path) as db:
                db.upsert({"inn": "1", "name": "В базе", "sources": ["rsmp"]})
                db.upsert({"inn": "9", "name": "Не в файле — не трогать", "sources": ["rsmp"]})

            inns_file = Path(tmp) / "inns.txt"
            inns_file.write_text("1\n2\nне-инн\n", encoding="utf-8")

            checked: list[str] = []

            def fake_check_membership(inn, session):
                checked.append(inn)
                return {"sro_member": 0, "sro_info": []}

            with patch("mosstroybase.cli.sro.check_membership", side_effect=fake_check_membership):
                rc = main(["--db", db_path, "enrich-sro", "--file", str(inns_file)])
            self.assertEqual(rc, 0)
            self.assertEqual(set(checked), {"1", "2"})

            with CompanyDB(db_path) as db:
                self.assertIsNotNone(db.get("2"))  # добавлен из файла
                self.assertIn("sro", db.get("1")["sources"])
                self.assertIn("sro", db.get("2")["sources"])
                self.assertNotIn("sro", db.get("9")["sources"])  # вне файла — не проверяли

    def test_resumes_without_rechecking_already_done(self):
        # На большом файле процесс может прерваться на середине — повторный
        # запуск с тем же файлом не должен переспрашивать уже проверенных
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "base.sqlite3")
            with CompanyDB(db_path) as db:
                db.upsert({"inn": "1", "name": "Уже проверен", "sources": ["sro"],
                           "sro_member": 0})
                db.upsert({"inn": "2", "name": "Ещё не проверен", "sources": ["rsmp"]})

            inns_file = Path(tmp) / "inns.txt"
            inns_file.write_text("1\n2\n", encoding="utf-8")

            checked: list[str] = []

            def fake_check_membership(inn, session):
                checked.append(inn)
                return {"sro_member": 0, "sro_info": []}

            with patch("mosstroybase.cli.sro.check_membership", side_effect=fake_check_membership):
                rc = main(["--db", db_path, "enrich-sro", "--file", str(inns_file)])
            self.assertEqual(rc, 0)
            self.assertEqual(checked, ["2"])  # "1" пропущен — уже был проверен

            # --recheck снимает пропуск и переспрашивает всех из файла заново
            checked.clear()
            with patch("mosstroybase.cli.sro.check_membership", side_effect=fake_check_membership):
                rc = main(["--db", db_path, "enrich-sro", "--file", str(inns_file), "--recheck"])
            self.assertEqual(rc, 0)
            self.assertEqual(set(checked), {"1", "2"})

    def test_out_writes_report_covering_whole_file_not_just_this_run(self):
        # "1" был проверен раньше (и потому пропущен этим запуском), "2" —
        # проверяется сейчас; отчёт --out должен покрывать ОБЕИХ, не только
        # тех, кого коснулся именно этот запуск
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "base.sqlite3")
            with CompanyDB(db_path) as db:
                db.upsert({"inn": "1", "name": 'ООО "Ранее проверен"', "sources": ["sro"],
                           "sro_member": 1, "sro_info": ["НОСТРОЙ: член строительной СРО"]})

            inns_file = Path(tmp) / "inns.txt"
            inns_file.write_text("1\n2\n", encoding="utf-8")
            out_csv = Path(tmp) / "результат.csv"

            def fake_check_membership(inn, session):
                return {"sro_member": 0, "sro_info": []}

            with patch("mosstroybase.cli.sro.check_membership", side_effect=fake_check_membership):
                rc = main(["--db", db_path, "enrich-sro", "--file", str(inns_file),
                           "--out", str(out_csv)])
            self.assertEqual(rc, 0)
            self.assertTrue(out_csv.exists())

            with open(out_csv, encoding="utf-8-sig") as fh:
                rows = list(csv.reader(fh, delimiter=";"))
            self.assertEqual(rows[0], ["ИНН", "Название", "Результат"])
            by_inn = {r[0]: r for r in rows[1:]}
            self.assertEqual(set(by_inn), {"1", "2"})
            self.assertIn("член строительной СРО", by_inn["1"][2])
            self.assertEqual(by_inn["2"][2], "не в НОСТРОЙ")


class TestEnrichNoprizFromFile(unittest.TestCase):
    def test_checks_file_inns_without_touching_export_filters(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "base.sqlite3")
            inns_file = Path(tmp) / "inns.txt"
            inns_file.write_text("7700000001\n7700000002\n", encoding="utf-8")

            def fake_check_membership(inn, session):
                # Первая — проектная (член НОПРИЗ), вторая — нет
                if inn == "7700000001":
                    return {"nopriz_member": 1, "nopriz_info": ["НОПРИЗ: член СРО"]}
                return {"nopriz_member": 0, "nopriz_info": []}

            with patch("mosstroybase.cli.nopriz.check_membership",
                       side_effect=fake_check_membership):
                rc = main(["--db", db_path, "enrich-nopriz", "--file", str(inns_file)])
            self.assertEqual(rc, 0)

            with CompanyDB(db_path) as db:
                self.assertEqual(db.get("7700000001")["nopriz_member"], 1)
                self.assertEqual(db.get("7700000002")["nopriz_member"], 0)
                # sro_member не тронут — НОПРИЗ не влияет на отсев по СРО
                self.assertIsNone(db.get("7700000001").get("sro_member"))

            # НОПРИЗ-членство не исключает из выгрузки (в отличие от sro_member)
            csv_path = str(Path(tmp) / "out.csv")
            main(["--db", db_path, "export", "--csv", csv_path])
            with open(csv_path, encoding="utf-8-sig") as fh:
                rows = list(csv.reader(fh, delimiter=";"))
            self.assertEqual({r[0] for r in rows[1:]}, {"7700000001", "7700000002"})


class TestTodaysCheckoInns(unittest.TestCase):
    def test_accumulates_across_runs_same_day(self):
        # Имитирует два запуска `daily` в один день с разными ключами Checko:
        # у обеих компаний source=checko и updated_at сегодня — обе должны
        # попасть в дневной файл, а не только последняя пачка
        with TemporaryDirectory() as tmp:
            with CompanyDB(str(Path(tmp) / "t.sqlite3")) as db:
                db.upsert({"inn": "1", "name": "Первый ключ", "sources": ["checko"]})
                db.upsert({"inn": "2", "name": "Второй ключ", "sources": ["checko"]})
                today = db.get("1")["updated_at"][:10]
                self.assertEqual(todays_checko_inns(db, today), {"1", "2"})

    def test_ignores_previous_days_and_non_checko_sources(self):
        with TemporaryDirectory() as tmp:
            with CompanyDB(str(Path(tmp) / "t.sqlite3")) as db:
                db.upsert({"inn": "1", "name": "Сегодня", "sources": ["checko"]})
                db.upsert({"inn": "2", "name": "Только СРО", "sources": ["sro"]})
                db.upsert({"inn": "3", "name": "Вчера", "sources": ["checko"]})
                db.conn.execute(
                    "UPDATE companies SET updated_at = ? WHERE inn = ?",
                    ("2020-01-01T00:00:00Z", "3"),
                )
                db.conn.commit()
                today = db.get("1")["updated_at"][:10]
                self.assertEqual(todays_checko_inns(db, today), {"1"})


if __name__ == "__main__":
    unittest.main()
