import unittest

from mosstroybase.sources import egrul

# Синтетический пример в духе JSON-конвертации выписки ЕГРЮЛ
SAMPLE_ACTIVE = {
    "СвЮЛ": {
        "@attributes": {"ИНН": "7701234567", "ОГРН": "1157746000001", "КодРегион": "77"},
        "СвНаимЮЛ": {
            "@attributes": {
                "НаимЮЛПолн": "ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \"СТРОЙМОНТАЖ\"",
                "НаимЮЛСокр": "ООО \"СТРОЙМОНТАЖ\"",
            }
        },
        "СвАдресЮЛ": {
            "АдресРФ": {
                "@attributes": {"Индекс": "101000", "КодРегион": "77", "Дом": "Д. 5"},
                "Регион": {"@attributes": {"ТипРегион": "ГОРОД", "НаимРегион": "МОСКВА"}},
                "Улица": {"@attributes": {"ТипУлица": "УЛИЦА", "НаимУлица": "МЯСНИЦКАЯ"}},
            },
            "СвАдрЮЛФИАС": {
                "ИдНом": "f26b876b-6857-4951-b060-ec6559f04a9a",
            },
        },
        "СвАдрЭлПочты": {"@attributes": {"E-mail": "Info@StroyMontazh.ru"}},
        "СвОКВЭД": {
            "СвОКВЭДОсн": {"@attributes": {"КодОКВЭД": "41.20", "НаимОКВЭД": "Строительство"}},
            "СвОКВЭДДоп": [
                {"@attributes": {"КодОКВЭД": "43.31"}},
                {"@attributes": {"КодОКВЭД": "43.32"}},
            ],
        },
    }
}

SAMPLE_TERMINATED = {
    "СвЮЛ": {
        "@attributes": {"ИНН": "7709999999"},
        "СвПрекрЮЛ": {"@attributes": {"ДатаПрекрЮЛ": "2020-01-15"}},
    }
}


class TestEgrulExtract(unittest.TestCase):
    def test_active_company(self):
        info = egrul.extract_info(SAMPLE_ACTIVE)
        self.assertEqual(info["is_active"], 1)
        self.assertIn("СТРОЙМОНТАЖ", info["name"])
        self.assertEqual(info["name_short"], 'ООО "СТРОЙМОНТАЖ"')
        self.assertEqual(info["emails"], ["info@stroymontazh.ru"])
        self.assertEqual(info["okved_main"], "41.20")
        self.assertEqual(info["okved_add"], ["43.31", "43.32"])
        self.assertEqual(info["region_code"], "77")
        # Адрес собран из смысловых полей, без GUID и кодов
        self.assertIn("МОСКВА", info["address"])
        self.assertIn("МЯСНИЦКАЯ", info["address"])
        self.assertNotIn("f26b876b", info["address"])

    def test_terminated_company(self):
        info = egrul.extract_info(SAMPLE_TERMINATED)
        self.assertEqual(info["is_active"], 0)
        self.assertEqual(info["emails"], [])


if __name__ == "__main__":
    unittest.main()
