"""Тесты валидации e-mail: синтаксис, стоп-листы, деобфускация, приоритеты."""
import pytest

from validators.email import EmailValidator, domain_of, extract_emails


@pytest.fixture
def validator() -> EmailValidator:
    return EmailValidator(
        stop_prefixes=["example", "test", "noreply", "no-reply", "your", "ваш"],
        stop_addresses=["email@site.ru", "ваш@почта.рф", "email@example.com"],
        dev_domains=["megagroup.ru", "bitrix24.ru", "tilda.cc"],
        free_domains=["mail.ru", "yandex.ru", "gmail.com"],
        check_mx=False,   # офлайн-тесты — без DNS
    )


class TestSyntax:
    def test_ok(self, validator):
        assert validator.syntax_ok("info@company.ru")

    def test_ok_subdomain(self, validator):
        assert validator.syntax_ok("a.b-c_d@mail.company.co.uk")

    def test_no_at(self, validator):
        assert not validator.syntax_ok("info.company.ru")

    def test_double_dot(self, validator):
        assert not validator.syntax_ok("info..x@company.ru")

    def test_no_tld(self, validator):
        assert not validator.syntax_ok("info@company")

    def test_file_name_not_email(self, validator):
        # logo@2x.png не должен считаться адресом
        assert not validator.syntax_ok("logo@2x.png")


class TestStopLists:
    def test_template_prefix(self, validator):
        v = validator.classify("test@company.ru")
        assert not v.valid and "шаблон" in v.reason

    def test_noreply(self, validator):
        assert not validator.classify("noreply@company.ru").valid

    def test_stop_address(self, validator):
        assert not validator.classify("ваш@почта.рф").valid

    def test_dev_studio_domain(self, validator):
        v = validator.classify("support@megagroup.ru")
        assert not v.valid and "веб-студии" in v.reason

    def test_placeholder_domain(self, validator):
        assert not validator.classify("info@example.com").valid

    def test_normal_passes(self, validator):
        assert validator.classify("info@company.ru").valid


class TestClassification:
    def test_free_mail_flag(self, validator):
        v = validator.classify("stroyka2000@mail.ru")
        assert v.valid and v.is_free_mail and not v.is_corporate

    def test_corporate_flag(self, validator):
        v = validator.classify("sales@company.ru", company_site_domain="company.ru")
        assert v.valid and v.is_corporate and not v.is_free_mail

    def test_corporate_with_www(self, validator):
        v = validator.classify("sales@company.ru", company_site_domain="www.company.ru")
        assert v.is_corporate

    def test_lowercased(self, validator):
        v = validator.classify("Sales@Company.RU")
        assert v.email == "sales@company.ru"


class TestExtractEmails:
    def test_plain(self):
        assert extract_emails("пишите на info@firma.ru или sales@firma.ru") == \
            ["info@firma.ru", "sales@firma.ru"]

    def test_obfuscated_at(self):
        assert extract_emails("почта: info (at) firma.ru") == ["info@firma.ru"]

    def test_obfuscated_sobaka(self):
        assert extract_emails("адрес: buh [собака] zavod [точка] ru") == ["buh@zavod.ru"]

    def test_obfuscated_a(self):
        assert extract_emails("op(a)stroy.ru") == ["op@stroy.ru"]

    def test_spaces_around_at(self):
        assert extract_emails("mail: office @ dom . ru") == ["office@dom.ru"]

    def test_dedup(self):
        assert extract_emails("a@b.ru a@b.ru A@B.RU") == ["a@b.ru"]

    def test_none_in_plain_text(self):
        assert extract_emails("обычный текст без адресов, находимся по адресу г. Москва") == []


class TestMx:
    def test_mx_disabled(self, validator):
        import asyncio

        v = asyncio.run(validator.validate("info@no-such-domain-xyz.ru"))
        assert v.valid and not v.mx_checked


def test_domain_of():
    assert domain_of("info@firma.ru") == "firma.ru"
    assert domain_of("https://www.firma.ru/contacts") == "firma.ru"
    assert domain_of("firma.ru") == "firma.ru"
