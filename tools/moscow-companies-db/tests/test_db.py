import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mosstroybase.db import CompanyDB


class TestCompanyDB(unittest.TestCase):
    def test_upsert_merges_contacts_and_sources(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "test.sqlite3")
            with CompanyDB(db_path) as db:
                db.upsert({
                    "inn": "7701234567",
                    "name": "ООО СТРОЙМОНТАЖ",
                    "okved_main": "41.20",
                    "emails": ["info@a.ru"],
                    "sources": ["rsmp"],
                })
                # Обогащение из другого источника дополняет запись
                db.upsert({
                    "inn": "7701234567",
                    "emails": ["sales@a.ru", "info@a.ru"],
                    "phones": ["+74951234567"],
                    "egrul_status": "Действует",
                    "is_active": 1,
                    "sources": ["egrul"],
                })
                company = db.get("7701234567")
                self.assertEqual(company["name"], "ООО СТРОЙМОНТАЖ")
                self.assertEqual(company["emails"], ["info@a.ru", "sales@a.ru"])
                self.assertEqual(company["phones"], ["+74951234567"])
                self.assertEqual(company["sources"], ["rsmp", "egrul"])
                self.assertEqual(company["is_active"], 1)

    def test_iter_missing_source(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "test.sqlite3")
            with CompanyDB(db_path) as db:
                db.upsert({"inn": "1", "sources": ["rsmp"]})
                db.upsert({"inn": "2", "sources": ["rsmp", "egrul"]})
                missing = [c["inn"] for c in db.iter_missing_source("egrul")]
                self.assertEqual(missing, ["1"])

    def test_empty_inn_ignored(self):
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "test.sqlite3")
            with CompanyDB(db_path) as db:
                db.upsert({"inn": "", "name": "x"})
                self.assertEqual(db.stats()["всего"], 0)


if __name__ == "__main__":
    unittest.main()
