import unittest

from mosstroybase.normalize import extract_emails, extract_phones, merge_unique, normalize_phone


class TestNormalize(unittest.TestCase):
    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("+7 (495) 123-45-67"), "+74951234567")
        self.assertEqual(normalize_phone("8 495 123 45 67"), "+74951234567")
        self.assertEqual(normalize_phone("74951234567"), "+74951234567")
        self.assertEqual(normalize_phone("4951234567"), "+74951234567")
        self.assertIsNone(normalize_phone("12345"))
        self.assertIsNone(normalize_phone("+7 000 000 00 00"))

    def test_extract_phones(self):
        text = "Тел.: +7 (495) 123-45-67, 8-926-000-11-22; факс +7 495 123 45 67"
        self.assertEqual(extract_phones(text), ["+74951234567", "+79260001122"])

    def test_extract_emails(self):
        text = 'Пишите: Info@Example.ru или <img src="logo@2x.png"> sales@stroy-msk.com'
        self.assertEqual(extract_emails(text), ["info@example.ru", "sales@stroy-msk.com"])

    def test_merge_unique(self):
        self.assertEqual(
            merge_unique(["a", "b"], None, ["b", "", "c"]),
            ["a", "b", "c"],
        )


if __name__ == "__main__":
    unittest.main()
