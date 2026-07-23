import unittest

from mosstroybase.sources import sro

INN = "7701234567"

# Синтетические ответы в духе API реестра НОСТРОЙ
PAYLOAD_MEMBER = {
    "data": {
        "data": [
            {
                "id": 123,
                "inn": INN,
                "full_description": 'ООО "СТРОЙМОНТАЖ"',
                "member_status": {"id": 1, "title": "Является членом"},
                "sro": {"title": "Ассоциация «Столичное строительное объединение»"},
            }
        ],
        "count": 1,
    }
}

PAYLOAD_FORMER = {
    "data": {
        "data": [
            {
                "inn": INN,
                "member_status": {"id": 2, "title": "Исключен"},
            }
        ],
        "count": 1,
    }
}

PAYLOAD_EMPTY = {"data": {"data": [], "count": 0}}

# Фильтр API мог не сработать и вернуть чужие записи — совпадения по ИНН нет
PAYLOAD_OTHER_INN = {
    "data": {
        "data": [{"inn": "9999999999", "member_status": {"title": "Является членом"}}],
        "count": 1,
    }
}

# ИНН числом, а не строкой
PAYLOAD_INT_INN = {"data": {"data": [{"inn": int(INN), "status": "Является членом"}]}}


class TestSroEvaluate(unittest.TestCase):
    def test_member(self):
        self.assertEqual(sro.evaluate(PAYLOAD_MEMBER, INN), "member")

    def test_former_member(self):
        self.assertEqual(sro.evaluate(PAYLOAD_FORMER, INN), "former")

    def test_not_found(self):
        self.assertIsNone(sro.evaluate(PAYLOAD_EMPTY, INN))

    def test_foreign_records_ignored(self):
        self.assertIsNone(sro.evaluate(PAYLOAD_OTHER_INN, INN))

    def test_inn_as_int(self):
        self.assertEqual(sro.evaluate(PAYLOAD_INT_INN, INN), "member")

    def test_garbage_payload(self):
        self.assertIsNone(sro.evaluate({"error": "oops"}, INN))
        self.assertIsNone(sro.evaluate(None, INN))


if __name__ == "__main__":
    unittest.main()
