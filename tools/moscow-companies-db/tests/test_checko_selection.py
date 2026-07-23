import unittest

from mosstroybase.cli import select_for_checko

COMPANIES = [
    # ликвидированная — квоту не тратим
    {"inn": "1", "is_active": 0, "phones": [], "okved_main": "41.20"},
    # телефон уже есть — квоту не тратим
    {"inn": "2", "is_active": 1, "phones": ["+74950000000"], "okved_main": "41.20"},
    # стройка по доп. ОКВЭД (основной — торговля) — во вторую очередь
    {"inn": "3", "is_active": 1, "phones": [], "okved_main": "46.73"},
    # основной строительный ОКВЭД — в первую очередь
    {"inn": "4", "is_active": 1, "phones": [], "okved_main": "43.99"},
    # статус ещё неизвестен (ЕГРЮЛ не запрашивался) — не отсеиваем
    {"inn": "5", "is_active": None, "phones": [], "okved_main": "71.12.45"},
]


class TestSelectForChecko(unittest.TestCase):
    def test_default_selection_and_priority(self):
        selected = select_for_checko(COMPANIES, limit=0)
        self.assertEqual([c["inn"] for c in selected], ["4", "5", "3"])

    def test_limit_takes_top_priority_first(self):
        selected = select_for_checko(COMPANIES, limit=2)
        self.assertEqual([c["inn"] for c in selected], ["4", "5"])

    def test_include_flags(self):
        selected = select_for_checko(
            COMPANIES, limit=0, include_inactive=True, include_with_phones=True
        )
        self.assertEqual({c["inn"] for c in selected}, {"1", "2", "3", "4", "5"})


if __name__ == "__main__":
    unittest.main()
