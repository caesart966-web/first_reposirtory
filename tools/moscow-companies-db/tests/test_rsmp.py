import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from mosstroybase.config import DEFAULT_OKVED_PREFIXES, MOSCOW_REGION_CODE
from mosstroybase.sources import rsmp

SAMPLE = Path(__file__).parent / "data" / "sample_rsmp.xml"


class TestRsmpParser(unittest.TestCase):
    def _collect(self, path, include_ip=False):
        return list(
            rsmp.iter_companies(
                path, MOSCOW_REGION_CODE, DEFAULT_OKVED_PREFIXES, include_ip=include_ip
            )
        )

    def test_filters_moscow_construction_orgs(self):
        companies = self._collect(SAMPLE)
        inns = {c["inn"] for c in companies}
        # Московская стройка (осн. ОКВЭД), проектирование/изыскания,
        # и торговая компания со строительным доп. ОКВЭД
        self.assertEqual(inns, {"7701234567", "7709876543", "7706666666"})
        # Питер (78), ИП и ИТ-компания отфильтрованы
        self.assertNotIn("7801111111", inns)
        self.assertNotIn("770301234567", inns)
        self.assertNotIn("7705555555", inns)

    def test_parsed_fields(self):
        by_inn = {c["inn"]: c for c in self._collect(SAMPLE)}
        stroy = by_inn["7701234567"]
        self.assertEqual(stroy["kind"], "ЮЛ")
        self.assertEqual(stroy["ogrn"], "1157746000001")
        self.assertIn("СТРОЙМОНТАЖ", stroy["name"])
        self.assertEqual(stroy["okved_main"], "41.20")
        self.assertEqual(stroy["okved_add"], ["43.31"])
        self.assertEqual(stroy["msp_category"], "микро")
        self.assertIn("МОСКВА", stroy["address"])

        geo = by_inn["7709876543"]
        self.assertEqual(geo["okved_main"], "71.12.45")

    def test_include_ip(self):
        companies = self._collect(SAMPLE, include_ip=True)
        ip = [c for c in companies if c["kind"] == "ИП"]
        self.assertEqual(len(ip), 1)
        self.assertEqual(ip[0]["inn"], "770301234567")
        self.assertIn("ИВАНОВ", ip[0]["name"])

    def test_reads_zip_archive(self):
        with TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "rsmp.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.write(SAMPLE, "data1.xml")
                zf.write(SAMPLE, "data2.xml")
            companies = self._collect(zip_path)
        # Два одинаковых файла в архиве → каждый документ встречается дважды
        self.assertEqual(len(companies), 6)

    def test_okved_matches(self):
        prefixes = DEFAULT_OKVED_PREFIXES
        for code in ("41.20", "42.11", "43.99", "71.11", "71.12.45"):
            self.assertTrue(rsmp.okved_matches(code, prefixes), code)
        for code in ("46.73", "62.01", "71.20", ""):
            self.assertFalse(rsmp.okved_matches(code, prefixes), code)


if __name__ == "__main__":
    unittest.main()
