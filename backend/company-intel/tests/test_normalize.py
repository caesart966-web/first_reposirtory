import pytest

from company_intel.normalize import (
    entity_kind_by_inn, format_phone_ru, is_role_email, name_key,
    normalize_company_name, normalize_domain, normalize_email, normalize_phone,
    registrable_domain, same_site, translit_ru, validate_inn, validate_kpp,
    validate_ogrn,
)


@pytest.mark.parametrize("raw,expected", [
    ("8 (495) 123-45-67", "+74951234567"),
    ("+7 495 123 45 67", "+74951234567"),
    ("4951234567", "+74951234567"),
    ("+7 (916) 000-11-22 доб. 145", "+79160001122"),
    ("+44 20 7946 0958", "+442079460958"),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["1234", "0000000000", "+7 111 111 11 11", "", "01.02.2024"])
def test_normalize_phone_rejects_junk(raw):
    assert normalize_phone(raw) is None


def test_format_phone_ru():
    assert format_phone_ru("+74951234567") == "+7 (495) 123-45-67"
    assert format_phone_ru("+442079460958") == "+442079460958"


@pytest.mark.parametrize("raw,expected", [
    ("  Info@Example-corp.RU ", "info@example-corp.ru"),
    ("mailto:Sales@example.ru?subject=hi", "sales@example.ru"),
    ("ivan (собака) mail.ru", "ivan@mail.ru"),
    ("ivan [at] mail [dot] ru", "ivan@mail.ru"),
])
def test_normalize_email(raw, expected):
    assert normalize_email(raw) == expected


@pytest.mark.parametrize("raw", [
    "logo@2x.png", "a@b", "user@example.com", "@example.ru", "no-at-sign.ru",
    "x@sentry.io", "два@собаки@mail.ru",
])
def test_normalize_email_rejects_junk(raw):
    assert normalize_email(raw) is None


def test_role_email():
    assert is_role_email("info@x.ru")
    assert is_role_email("zakaz@x.ru")
    assert not is_role_email("i.petrov@x.ru")


@pytest.mark.parametrize("inn,valid", [
    ("7707083893", True),      # Сбербанк, юрлицо
    ("7707083894", False),     # испорченная контрольная цифра
    ("500100732259", True),    # 12 знаков, ИП
    ("500100732258", False),
    ("77070838", False),
])
def test_validate_inn(inn, valid):
    assert validate_inn(inn) is valid


@pytest.mark.parametrize("ogrn,valid", [
    ("1027700132195", True),
    ("1027700132196", False),
    ("304500116000157", True),
    ("12345", False),
])
def test_validate_ogrn(ogrn, valid):
    assert validate_ogrn(ogrn) is valid


def test_validate_kpp_and_entity_kind():
    assert validate_kpp("773601001")
    assert not validate_kpp("77360100")
    assert entity_kind_by_inn("7707083893") == "organization"
    assert entity_kind_by_inn("500100732259") == "individual"
    assert entity_kind_by_inn("123") is None


@pytest.mark.parametrize("raw,expected", [
    ("https://WWW.Example.RU/contacts?x=1", "example.ru"),
    ("example.ru", "example.ru"),
    ("http://mail.corp.example.co.uk:8080/", "mail.corp.example.co.uk"),
    ("не домен", None),
    ("localhost", None),
])
def test_normalize_domain(raw, expected):
    assert normalize_domain(raw) == expected


def test_registrable_domain_and_same_site():
    assert registrable_domain("mail.corp.example.co.uk") == "example.co.uk"
    assert registrable_domain("shop.example.ru") == "example.ru"
    assert same_site("https://shop.example.ru/x", "example.ru")
    assert not same_site("example.ru", "example.com")


def test_company_name_and_key():
    assert normalize_company_name('  ООО   «Ромашка-Строй» ') == 'ООО "Ромашка-Строй"'
    assert name_key('ООО «Ромашка-Строй»') == name_key('Ромашка-Строй')


def test_translit():
    assert translit_ru("Щербакова") == "shcherbakova"
    assert translit_ru("Иванов") == "ivanov"
    assert translit_ru("Юлия") == "yuliya"
