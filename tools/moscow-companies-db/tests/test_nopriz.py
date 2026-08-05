import unittest
from datetime import date, timedelta

from mosstroybase.sources import nopriz

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


FOREIGN_LISTING = {
    "data": {
        "data": [
            {"inn": "5907056036", "full_description": 'ООО "Проект-59"',
             "member_status": {"id": 2, "title": "Исключен"}},
        ],
        "count": 100000,
    }
}

MATCH_MEMBER = {
    "data": {
        "data": [
            {"inn": INN, "full_description": 'ООО "Тест"',
             "member_status": {"id": 1, "title": "Является членом"}},
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


class TestNoprizEvaluate(unittest.TestCase):
    def test_member(self):
        self.assertEqual(nopriz.evaluate(MATCH_MEMBER, INN), "member")

    def test_former(self):
        self.assertEqual(nopriz.evaluate(MATCH_FORMER, INN), "former")

    def test_not_found(self):
        self.assertIsNone(nopriz.evaluate(EMPTY, INN))

    def test_garbage_payload(self):
        self.assertIsNone(nopriz.evaluate({"error": "oops"}, INN))
        self.assertIsNone(nopriz.evaluate(None, INN))


class TestNoprizCheckMembership(unittest.TestCase):
    def setUp(self):
        nopriz._working_body = None
        nopriz._format_unusable = False

    def test_ignored_filter_then_working_variant(self):
        session = FakeSession([FOREIGN_LISTING, MATCH_MEMBER])
        result = nopriz.check_membership(INN, session)
        self.assertEqual(result["nopriz_member"], 1)
        self.assertEqual(nopriz._working_body, 1)

    def test_empty_response_means_not_member(self):
        session = FakeSession([EMPTY])
        result = nopriz.check_membership(INN, session)
        self.assertEqual(result, {"nopriz_member": 0, "nopriz_info": []})

    def test_former_member_recently_excluded_still_marked_member(self):
        # У НОПРИЗ (в отличие от sro.py) это чисто информационная проверка,
        # но давность исключения по-прежнему учитывается при вердикте
        session = FakeSession([former_payload(100)])
        result = nopriz.check_membership(INN, session)
        self.assertEqual(result["nopriz_member"], 1)
        self.assertIn("не раньше", result["nopriz_info"][0])

    def test_long_excluded_not_member(self):
        session = FakeSession([former_payload(400)])
        result = nopriz.check_membership(INN, session)
        self.assertEqual(result["nopriz_member"], 0)
        self.assertIn("год прошёл", result["nopriz_info"][0])

    def test_all_variants_ignored_returns_unknown(self):
        session = FakeSession([FOREIGN_LISTING])
        result = nopriz.check_membership(INN, session)
        self.assertIsNone(result)
        self.assertTrue(nopriz._format_unusable)
        calls_before = len(session.calls)
        self.assertIsNone(nopriz.check_membership(INN, session))
        self.assertEqual(len(session.calls), calls_before)

    def test_cached_variant_tried_first(self):
        nopriz._working_body = 2
        session = FakeSession([MATCH_MEMBER])
        result = nopriz.check_membership(INN, session)
        self.assertEqual(result["nopriz_member"], 1)
        self.assertIn("searchString", session.calls[0])

    def test_independent_cache_from_sro_module(self):
        # nopriz и sro — разные реестры с разными рабочими форматами фильтра;
        # состояние одного модуля не должно течь в другой
        from mosstroybase.sources import sro
        sro._working_body = 4
        sro._format_unusable = False
        nopriz._working_body = None
        self.assertNotEqual(nopriz._working_body, sro._working_body)


if __name__ == "__main__":
    unittest.main()
