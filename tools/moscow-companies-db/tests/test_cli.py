import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mosstroybase.cli import main

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
            self.assertEqual(inns, {"7701234567", "7709876543", "7706666666"})

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


if __name__ == "__main__":
    unittest.main()
