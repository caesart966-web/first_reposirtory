from company_intel.extract import (
    classify_social, extract_addresses, extract_emails, extract_persons,
    extract_phones, extract_requisites, parse_page,
)


def test_phones_from_page(contacts_html):
    page = parse_page(contacts_html, "https://romashka-stroy.ru/contacts")
    numbers = {p for p, _, _ in page.phones}
    assert numbers == {
        "+74951203344", "+78126401590", "+78126401591",
        "+78002001590", "+79167450011",
    }
    labels = {p: label for p, _, label in page.phones}
    assert labels["+78126401591"] == "fax"
    assert labels["+79167450011"] == "whatsapp"
    extensions = {p: ext for p, ext, _ in page.phones}
    assert extensions["+74951203344"] == "210"


def test_bank_details_are_not_phones():
    text = "Расчётный счёт 40702810100000001234, БИК 044525225, ИНН 7707083893"
    assert extract_phones(text) == []


def test_order_number_and_date_are_not_phones():
    assert extract_phones("Заказ №1234567890 от 01.02.2024") == []


def test_emails_including_obfuscated(contacts_html):
    page = parse_page(contacts_html, "https://romashka-stroy.ru/contacts")
    assert "info@romashka-stroy.ru" in page.emails
    assert "zakupki@romashka-stroy.ru" in page.emails   # «(собака)»
    assert "dev@webstudio-x.ru" in page.emails          # чужой домен — фильтруется позже


def test_requisites_checksum_filtering():
    good = extract_requisites("ИНН 7707083893, ОГРН 1027700132195, КПП 773601001")
    assert good == {"inn": ["7707083893"], "ogrn": ["1027700132195"], "kpp": ["773601001"]}
    bad = extract_requisites("ИНН 7707083894, ОГРН 1027700132196")
    assert bad == {}


def test_persons_and_positions(contacts_html):
    page = parse_page(contacts_html, "https://romashka-stroy.ru/contacts")
    people = dict(page.persons)
    assert people["Иванов Сергей Петрович"] == "генеральный директор"
    assert people["Щербакова Анна Юрьевна"] == "главный инженер"


def test_addresses():
    found = extract_addresses("Адрес: 190005, г. Санкт-Петербург, ул. Егорова, д. 25, оф. 412")
    assert any("Егорова" in a for a in found)


def test_socials_and_share_links():
    assert classify_social("https://vk.com/romashka") == ("vk", "https://vk.com/romashka")
    assert classify_social("https://t.me/romashka")[0] == "telegram"
    assert classify_social("https://facebook.com/sharer.php?u=x") is None
    assert classify_social("https://example.ru/page") is None


def test_internal_and_external_links(contacts_html):
    page = parse_page(contacts_html, "https://romashka-stroy.ru/contacts")
    assert "https://romashka-stroy.ru/rekvizity" in page.links
    assert "https://webstudio-x.ru" in page.external
