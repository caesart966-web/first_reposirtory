import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mosstroybase.db import CompanyDB
from mosstroybase.export import export_csv


class TestExport(unittest.TestCase):
    def _make_db(self, tmp: str) -> CompanyDB:
        db = CompanyDB(str(Path(tmp) / "t.sqlite3"))
        db.upsert({"inn": "1", "name": "А", "phones": ["+74950000001"], "is_active": 1})
        db.upsert({"inn": "2", "name": "Б", "is_active": 1})
        db.upsert({"inn": "3", "name": "В", "phones": ["+74950000003"], "is_active": 0})
        return db

    def _inns(self, path: str) -> set[str]:
        with open(path, encoding="utf-8-sig") as fh:
            return {row[0] for row in list(csv.reader(fh, delimiter=";"))[1:]}

    def test_filter_by_inns(self):
        with TemporaryDirectory() as tmp:
            with self._make_db(tmp) as db:
                out = str(Path(tmp) / "out.csv")
                n = export_csv(db, out, only_active=False, with_contacts_only=False,
                               inns={"1", "3"})
                self.assertEqual(n, 2)
                self.assertEqual(self._inns(out), {"1", "3"})

    def test_active_with_contacts(self):
        with TemporaryDirectory() as tmp:
            with self._make_db(tmp) as db:
                out = str(Path(tmp) / "out.csv")
                export_csv(db, out, only_active=True, with_contacts_only=True)
                self.assertEqual(self._inns(out), {"1"})


if __name__ == "__main__":
    unittest.main()
