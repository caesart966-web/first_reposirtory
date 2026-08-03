import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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
