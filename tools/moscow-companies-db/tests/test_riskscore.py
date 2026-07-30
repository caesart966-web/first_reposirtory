import unittest

from mosstroybase import riskscore


def _company(**kwargs) -> dict:
    base = {
        "inn": "1", "egrul_status": "Действует", "phones": ["+74950000001"],
        "phones_site": [], "emails": [], "website": "example.ru",
        "employees": 5, "taxes_paid": 100.0,
    }
    base.update(kwargs)
    return base


class TestRiskScore(unittest.TestCase):
    def test_clean_company_scores_low(self):
        score, reasons = riskscore.score_company(_company())
        self.assertLess(score, riskscore.CHECK_THRESHOLD)
        self.assertEqual(reasons, [])

    def test_egrul_exclusion_flagged_as_junk(self):
        company = _company(
            egrul_status="Регистрирующим органом принято решение о предстоящем "
                          "исключении юридического лица из ЕГРЮЛ"
        )
        score, reasons = riskscore.score_company(company)
        self.assertGreaterEqual(score, riskscore.JUNK_THRESHOLD)
        self.assertTrue(any("исключен" in r for r in reasons))

    def test_inactive_status_flagged_as_junk(self):
        score, _reasons = riskscore.score_company(_company(egrul_status="Не действует"))
        self.assertGreaterEqual(score, riskscore.JUNK_THRESHOLD)

    def test_no_contacts_at_all(self):
        score, reasons = riskscore.score_company(
            _company(phones=[], phones_site=[], emails=[], website=None)
        )
        self.assertTrue(any("нет контактов" in r for r in reasons))
        self.assertGreaterEqual(score, riskscore.CHECK_THRESHOLD)

    def test_free_email_only_no_site_is_a_minor_flag(self):
        score, reasons = riskscore.score_company(
            _company(phones=["+74950000001"], emails=["a@mail.ru"], website=None)
        )
        self.assertTrue(any("бесплатная почта" in r for r in reasons))
        self.assertLess(score, riskscore.CHECK_THRESHOLD)

    def test_zero_employees_and_taxes(self):
        score, reasons = riskscore.score_company(_company(employees=0, taxes_paid=0.0))
        self.assertTrue(any("0 сотрудников" in r for r in reasons))
        self.assertGreaterEqual(score, riskscore.CHECK_THRESHOLD)

    def test_missing_liveness_is_informational_only(self):
        score, reasons = riskscore.score_company(_company(employees=None, taxes_paid=None))
        self.assertTrue(any("не запрошены" in r for r in reasons))
        self.assertLess(score, riskscore.CHECK_THRESHOLD)

    def test_paired_registration_detected_across_batch(self):
        pair = [
            _company(inn="1", address="г. Москва, ул. Ленина, д. 1", reg_date="2024-01-10"),
            _company(inn="2", address="г. Москва, ул. Ленина, д. 1", reg_date="2024-01-15"),
            _company(inn="3", address="г. Москва, ул. Мира, д. 5", reg_date="2024-06-01"),
        ]
        scores = riskscore.score_all(pair)
        self.assertTrue(any("парная регистрация" in r for r in scores["1"][1]))
        self.assertTrue(any("парная регистрация" in r for r in scores["2"][1]))
        self.assertEqual(scores["3"][1], [])

    def test_same_address_far_apart_in_time_not_paired(self):
        pair = [
            _company(inn="1", address="г. Москва, БЦ Альфа", reg_date="2015-01-10"),
            _company(inn="2", address="г. Москва, БЦ Альфа", reg_date="2023-06-01"),
        ]
        scores = riskscore.score_all(pair)
        self.assertFalse(any("парная регистрация" in r for r in scores["1"][1]))


if __name__ == "__main__":
    unittest.main()
