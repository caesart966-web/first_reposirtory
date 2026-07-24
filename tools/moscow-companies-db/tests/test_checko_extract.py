import unittest

from mosstroybase.sources import checko

# Форма ответа Checko API v2 /company, снятая с реального ответа
DATA = {
    "ОГРН": "1207700214600",
    "ИНН": "0224955399",
    "НаимСокр": 'ООО "ФОРЕСТ"',
    "Статус": {"Код": "001", "Наим": "Действует"},
    "Регион": {"Код": "77", "Наим": "Москва"},
    "ЮрАдрес": {
        "НасПункт": "г. Москва",
        "АдресРФ": "125466, г. Москва, ул. Родионовская, д. 18, кв. 76",
        "МассАдрес": ["1137746957809"],
    },
    "ОКВЭД": {"Код": "43.12", "Наим": "Подготовка строительной площадки"},
    # Телефоны приходят СПИСКОМ строк — регресс-тест на обход списков
    "Контакты": {
        "Тел": ["+78212319428", "+7 (495) 111-22-33"],
        "Емэйл": ["Info@Forest-Profil.ru"],
        "ВебСайт": "forest-profil.ru",
    },
    "Руковод": [{
        "ФИО": "Родных Геннадий Геннадиевич",
        "ИНН": "110100129416",
        "ВидДолжн": "РУКОВОДИТЕЛЬ ЮРИДИЧЕСКОГО ЛИЦА",
        "НаимДолжн": "ГЕНЕРАЛЬНЫЙ ДИРЕКТОР",
        "Недост": False,
    }],
    # Похожие ключи не должны подменять руководителя
    "СвязРуковод": ["1177700022048"],
    "МассРуковод": False,
}


class TestCheckoExtract(unittest.TestCase):
    def test_full_extraction(self):
        info = checko.extract_contacts(DATA)
        self.assertEqual(info["phones"], ["+78212319428", "+74951112233"])
        self.assertEqual(info["emails"], ["info@forest-profil.ru"])
        self.assertEqual(info["website"], "forest-profil.ru")
        self.assertIn("Родионовская", info["address"])
        self.assertEqual(info["is_active"], 1)
        self.assertEqual(info["director"], "Родных Геннадий Геннадиевич")
        self.assertEqual(info["director_post"], "Генеральный директор")

    def test_no_contacts_block(self):
        data = {k: v for k, v in DATA.items() if k != "Контакты"}
        info = checko.extract_contacts(data)
        self.assertEqual(info["phones"], [])
        self.assertEqual(info["emails"], [])
        self.assertIsNone(info["website"])