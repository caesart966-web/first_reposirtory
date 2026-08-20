import unittest

from mosstroybase import links


def _c(inn, director=None, address=None, phones=None):
    return {"inn": inn, "director": director, "address": address,
            "phones": phones or [], "phones_site": []}


class TestPreciseAddress(unittest.TestCase):
    def test_coarse_addresses_rejected(self):
        # Реестр МСП отдаёт только город — по такому адресу связывать нельзя,
        # иначе вся московская база схлопнется в одну группу
        for coarse in ("г. Москва", "Москва", "г. Санкт-Петербург",
                       "Регион Москва, Город Москва", ""):
            self.assertFalse(links.is_precise_address(coarse), coarse)

    def test_precise_addresses_accepted(self):
        for precise in (
            "125466, г. Москва, ул. Родионовская, д. 18, кв. 76",
            "г. Москва, вн. тер. г. муниципальный округ Нагатино, Хлебозаводский проезд, д. 7, стр. 9",
            "199034, г. Санкт-Петербург, линия 13-я В.О., дом 6-8, литер А",
        ):
            self.assertTrue(links.is_precise_address(precise), precise)


class TestNormalization(unittest.TestCase):
    def test_fio_case_and_yo(self):
        self.assertEqual(links.normalize_name("Артёмов  Пётр   Иванович"),
                         links.normalize_name("артемов петр иванович"))

    def test_address_index_stripped(self):
        a = links.normalize_address("125466, г. Москва, ул. Ленина, д. 1")
        b = links.normalize_address("г. Москва, ул. Ленина, д. 1")
        self.assertEqual(a, b)


class TestFindGroups(unittest.TestCase):
    def test_groups_by_director(self):
        companies = [
            _c("1", director="Иванов Иван Иванович"),
            _c("2", director="Иванов Иван Иванович"),
            _c("3", director="Петров Пётр Петрович"),
        ]
        groups = links.find_groups(companies)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["inns"], ["1", "2"])

    def test_coarse_address_does_not_group(self):
        # Ключевая защита: у всех «г. Москва», но связи быть не должно
        companies = [_c(str(i), address="г. Москва") for i in range(50)]
        self.assertEqual(links.find_groups(companies, kinds=("адрес",)), [])

    def test_precise_address_groups(self):
        addr = "125466, г. Москва, ул. Родионовская, д. 18"
        companies = [_c("1", address=addr), _c("2", address=addr), _c("3", address=None)]
        groups = links.find_groups(companies, kinds=("адрес",))
        self.assertEqual([g["inns"] for g in groups], [["1", "2"]])

    def test_transitive_linking(self):
        # A—B по директору, B—C по телефону: все трое в одной группе
        companies = [
            _c("1", director="Иванов Иван Иванович"),
            _c("2", director="Иванов Иван Иванович", phones=["+74950000001"]),
            _c("3", phones=["+74950000001"]),
        ]
        groups = links.find_groups(companies, kinds=("директор", "телефон"))
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["inns"], ["1", "2", "3"])

    def test_kinds_limit_what_links(self):
        # Тот же набор, но связываем только по директору — «3» отваливается
        companies = [
            _c("1", director="Иванов Иван Иванович"),
            _c("2", director="Иванов Иван Иванович", phones=["+74950000001"]),
            _c("3", phones=["+74950000001"]),
        ]
        groups = links.find_groups(companies, kinds=("директор",))
        self.assertEqual([g["inns"] for g in groups], [["1", "2"]])

    def test_junk_director_ignored(self):
        for junk in ("", "  ", "нет", "-"):
            companies = [_c("1", director=junk), _c("2", director=junk)]
            self.assertEqual(links.find_groups(companies, kinds=("директор",)), [],
                             f"мусорный директор «{junk}» связал компании")

    def test_groups_sorted_by_size(self):
        companies = ([_c(str(i), director="Иванов Иван Иванович") for i in range(5)] +
                     [_c("a", director="Петров Пётр Петрович"),
                      _c("b", director="Петров Пётр Петрович")])
        sizes = [len(g["inns"]) for g in links.find_groups(companies)]
        self.assertEqual(sizes, [5, 2])

    def test_min_size(self):
        companies = ([_c(str(i), director="Иванов Иван Иванович") for i in range(3)] +
                     [_c("a", director="Петров Пётр Петрович"),
                      _c("b", director="Петров Пётр Петрович")])
        groups = links.find_groups(companies, min_size=3)
        self.assertEqual([len(g["inns"]) for g in groups], [3])

    def test_reasons_reported(self):
        companies = [
            _c("1", director="Иванов Иван Иванович"),
            _c("2", director="Иванов Иван Иванович"),
        ]
        reasons = links.find_groups(companies)[0]["reasons"]
        self.assertEqual(reasons[0][0], "директор")
        self.assertEqual(reasons[0][2], 2)
        self.assertIn("директор", links.describe(reasons))

    def test_scale_does_not_hang(self):
        # 60 тысяч компаний, много общих директоров — должно считаться быстро
        import time
        companies = [_c(str(i), director=f"Директор №{i % 5000} Иванович")
                     for i in range(60000)]
        started = time.monotonic()
        groups = links.find_groups(companies)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 10.0, f"find_groups занял {elapsed:.1f}с")
        self.assertEqual(len(groups), 5000)


if __name__ == "__main__":
    unittest.main()
