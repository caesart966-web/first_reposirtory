"""Тесты парсера контактной страницы на сохранённом HTML (без сети)."""
from pathlib import Path

import pytest

from connectors.website import parse_contact_page

FIXTURE = Path(__file__).parent / "fixtures" / "contacts_page.html"


@pytest.fixture(scope="module")
def page():
    html = FIXTURE.read_text(encoding="utf-8")
    return parse_contact_page(html, base_url="https://stroygarant-test.ru/kontakty")


class TestEmails:
    def test_mailto_found(self, page):
        assert "sales@stroygarant-test.ru" in page.emails

    def test_jsonld_email_found(self, page):
        assert "office@stroygarant-test.ru" in page.emails

    def test_obfuscated_at_found(self, page):
        assert "snab@stroygarant-test.ru" in page.emails

    def test_obfuscated_sobaka_tochka_found(self, page):
        assert "buh@stroygarant-test.ru" in page.emails

    def test_dev_studio_email_present_before_filtering(self, page):
        # парсер собирает всё; отсев студии — задача EmailValidator по стоп-листу
        assert "support@megagroup.ru" in page.emails

    def test_no_duplicates(self, page):
        assert len(page.emails) == len(set(page.emails))


class TestPhones:
    def test_tel_link(self, page):
        assert "+74951234567" in page.phones

    def test_toll_free_from_text(self, page):
        assert "+78005553535" in page.phones

    def test_mobile_from_text(self, page):
        assert "+79261112233" in page.phones

    def test_normalized_format(self, page):
        assert all(p.startswith("+7") and len(p) == 12 for p in page.phones)


class TestSocials:
    def _networks(self, page):
        return {network for network, _, _ in page.socials}

    def test_vk(self, page):
        assert "vk" in self._networks(page)

    def test_telegram(self, page):
        assert "telegram" in self._networks(page)

    def test_whatsapp(self, page):
        assert "whatsapp" in self._networks(page)

    def test_ok(self, page):
        assert "ok" in self._networks(page)

    def test_kinds(self, page):
        kinds = {network: kind for network, _, kind in page.socials}
        assert kinds["telegram"] == "messenger"
        assert kinds["vk"] == "social"


class TestVerification:
    def test_inn_found_in_footer(self, page):
        assert "7707083893" in page.inns_found

    def test_org_name_from_jsonld_and_title(self, page):
        assert any("СтройГарант" in name for name in page.org_names)


class TestContactLinks:
    def test_contact_page_link_discovered(self, page):
        assert any(link.endswith("/kontakty") for link in page.contact_links)

    def test_about_link_discovered(self, page):
        assert any(link.endswith("/about") for link in page.contact_links)


def test_empty_html_ok():
    page = parse_contact_page("", base_url="https://x.ru")
    assert page.emails == [] and page.phones == [] and page.socials == []


def test_broken_html_ok():
    page = parse_contact_page("<div><a href='mailto:a@b.ru'>почта", base_url="")
    assert page.emails == ["a@b.ru"]
