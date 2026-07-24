import unittest
from datetime import date, timedelta

from mosstroybase.sources import sro

INN = "6162005910"


def former_payload(days_ago: int) -> dict:
    stop = (date.today() - timedelta(days=days_ago)).strftime("%d.%m.%Y") + " 00:00:00"
    return {
        "data": {
            "data": [{
                "inn": INN,
                "member_status": {"id": 2, "title": "Исключен"},
                "member_right_stop_date_time_string": stop,
            }],
            "count": 1,
        }
    }

# Ответ с проигнорированным фильтром: общий список, чужие ИНН
FOREIGN_LISTING = {
    "data": {
        "data": [
            {"inn": "5907056036", "full_description": 'ООО "СтройМонтаж-59"',
             "member_status": {"id": 2, "title": "Исключен"}},
        ],
        "count": 100000,
    }
}

MATCH_MEMBER = {
    "data": {
        "data": [
            {"inn": INN, "full_description": 'ООО "Тест"',
             "member_status": {"id": 1, "title": "Является членом"},
             "director": "директор Иванов Иван Иванович"},
        ],
        "count": 1,
    }
}

MATCH_FORMER = {
    "data": {"data": [{"inn": INN, "member_status": {"title": "Исключен"}}], "count": 1}
}

EMPTY = {"data": {"data": [], "count": 0}}


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    """Отдаёт ответы по порядку вызовов; последний повторяется."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append(json)
        idx = min(len(self.calls) - 1, len(self._payloads) - 1)
        return FakeResponse(self._payloads[idx])


class TestCheckMembership(unittest.TestCase):
    def setUp(self):
        sro._working_body = None
        sro._format_unusable = False

    def test_ignored_filter_then_working_variant(self):
        # 1-й формат игнорируется (чужой список), 2-й фильтрует и находит члена
        session = FakeSession([FOREIGN_LISTING, MATCH_MEMBER])
        result = sro.check_membership(INN, session)
        self.assertEqual(result["sro_member"], 1)
        self.assertEqual(sro._working_body, 1)  # рабочий формат закеширован

    def test_empty_response_means_not_member(self):
        session = FakeSession([EMPTY])
        result = sro.check_membership(INN, session)
        self.assertEqual(result, {"sro_member": 0, "sro_info": []})
        self.assertEqual(sro._working_body, 0)

    def test_former_member_without_date_kept_as_lead(self):
        session = FakeSession([MATCH_FORMER])
        result = sro.check_membership(INN, session)
        self.assertEqual(result["sro_member"], 0)
        self.assertIn("исключён", result["sro_info"][0])
        self.assertIn("проверьте вручную", result["sro_info"][0])

    def test_recently_excluded_blocked_for_a_year(self):
        # Исключён 100 дней назад — вступить в СРО ещё нельзя, отсекаем
        session = FakeSession([former_payload(100)])
        result = sro.check_membership(INN, session)
        self.assertEqual(result["sro_member"], 1)
        self.assertIn("не раньше", result["sro_info"][0])

    def test_long_excluded_is_lead(self):
        # Исключён 400 дней назад — год прошёл, полноценный лид
        session = FakeSession([former_payload(400)])
        result = sro.check_membership(INN, session)
        self.assertEqual(result["sro_member"], 0)
        self.assertIn("год прошёл", result["sro_info"][0])

    def test_all_variants_ignored_returns_unknown(self):
        session = FakeSession([FOREIGN_LISTING])
        result = sro.check_membership(INN, session)
        self.assertIsNone(result)
        self.assertTrue(sro._format_unusable)
        # повторный вызов не ходит в сеть
        calls_before = len(session.calls)
        self.assertIsNone(sro.check_membership(INN, session))
        self.assertEqual(len(session.calls), calls_before)

    def test_cached_variant_tried_first(self):
        sro._working_body = 2
        session = FakeSession([MATCH_MEMBER])
        result = sro.check_membership(INN, session)
        self.assertEqual(result["sro_member"], 1)
        # первый же запрос использовал закешированный формат №3 (searchString)
        self.assertIn("searchString", session.calls[0])


if __name__ == "__main__":
    unittest.main()
