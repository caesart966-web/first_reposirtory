from openpyxl import Workbook

from core.enrich import Enricher, extract_contacts, name_core
from core.models import EXCLUDED_FROM_SRO, Org, Signal
from core.scoring import rescore_all
from core.utils import resolve_path


def test_extract_contacts():
    html = """<html><body><a href="mailto:Info@Firm.ru?subject=x">почта</a>
    <a href="tel:+7 (812) 123-45-67">звоните</a> Телефон: 8 812 765-43-21, e-mail: sales@firm.ru
    <img src="logo@2x.png"> <script>var a='bot@example.com'</script></body></html>"""
    emails, phones = extract_contacts(html)
    assert emails == ["info@firm.ru", "sales@firm.ru"]
    assert phones == ["+7 (812) 123-45-67", "+7 (812) 765-43-21"]


def test_name_core():
    assert name_core('ООО "ГАЛЕОН"') == "галеон"
    assert name_core("ООО Строительная компания") is None


def test_parse_dadata():
    sug = {"value": 'ООО "ГАЛЕОН"', "data": {
        "ogrn": "1257800009994", "type": "LEGAL", "okved": "41.20",
        "name": {"short_with_opf": 'ООО "ГАЛЕОН"'},
        "management": {"name": "Мухтаров Дмитрий Владимирович"},
        "state": {"status": "ACTIVE"},
        "address": {"value": "г Санкт-Петербург, ул Смолячкова, д 19", "data": {"region_with_type": "г Санкт-Петербург"}},
        "emails": [{"value": "a@b.ru"}], "phones": None}}
    org = Enricher.parse_dadata("7802961682", sug)
    assert org.name == 'ООО "ГАЛЕОН"' and org.ogrn == "1257800009994" and org.region == "г Санкт-Петербург"
    assert org.director == "Мухтаров Дмитрий Владимирович" and org.status == "ACTIVE" and org.email == "a@b.ru"
    ip = {"value": "ИП Иванов", "data": {"type": "INDIVIDUAL", "fio": {"surname": "Иванов", "name": "Иван"},
                                          "state": {"status": "LIQUIDATED"}, "address": {"value": "Ленинградская обл, г Гатчина"}}}
    org = Enricher.parse_dadata("470000000001", ip)
    assert org.director == "Иванов Иван" and org.status == "LIQUIDATED" and org.region == "Ленинградская обл"


def make_directory(path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Название", "ИНН", "КПП", "Адрес", "Фамилия руководителя", "Имя руководителя", "Отчество руководителя",
               "Вид деятельности", "Телефоны", "email", "Сайт", "ОГРН"])
    ws.append(['ООО "ГАЛЕОН"', 7802961682, "780201001", "195277, г. Санкт-Петербург, ул. Смолячкова", "Мухтаров", "Дмитрий",
               "Владимирович", "Строительство", "+7 (812) 648-02-63", "ooogaleon@yahoo.com", None, "1257800009994"])
    wb.save(path)


def test_local_directory_and_enrich_pipeline(cfg, db):
    make_directory(resolve_path(cfg, "companies_dir") / "spb.xlsx")
    db.add_signals([Signal("7802961682", EXCLUDED_FROM_SRO, "2026-02-01", "nostroy"),
                    Signal("7800000001", EXCLUDED_FROM_SRO, "2026-02-01", "nostroy")])
    rescore_all(db, cfg, "2026-02-03")
    e = Enricher(cfg, db)
    assert set(e.candidates(10)) == {"7802961682", "7800000001"}
    stats = e.run()
    assert stats["enriched"] == 2 and stats["errors"] == 0
    org = db.get_org("7802961682")
    assert org.phone == "+7 (812) 648-02-63" and org.email == "ooogaleon@yahoo.com"
    assert org.director == "Мухтаров Дмитрий Владимирович" and org.ogrn == "1257800009994"
    assert org.enriched_at
    assert e.candidates(10) == []          # повторно не обогащаем раньше 30 дней


def test_upsert_org_does_not_erase_fields(db):
    db.upsert_org(Org(inn="1000000001", name="A", phone="1"))
    db.upsert_org(Org(inn="1000000001", email="x@y"))
    o = db.get_org("1000000001")
    assert o.name == "A" and o.phone == "1" and o.email == "x@y"


class FakeResp:
    def __init__(self, html, status=200):
        self.status_code = status
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"
        self._data = html.encode("utf-8")
        self.text = html

    class _Raw:
        def __init__(self, data):
            self.data = data

        def read(self, n, decode_content=True):
            return self.data[:n]

    @property
    def raw(self):
        return self._Raw(self._data)


class FakeHttp:
    """Сайты по домену: pages[домен][путь] -> html; поисковая выдача — search_html."""

    def __init__(self, pages, search_html=""):
        self.pages = pages
        self.search_html = search_html

    def get(self, url, **kw):
        if "duckduckgo" in url:
            return FakeResp(self.search_html)
        from urllib.parse import urlparse
        u = urlparse(url)
        html = self.pages.get(u.netloc, {}).get(u.path or "/")
        return FakeResp(html) if html is not None else FakeResp("", 404)


def enricher_with_site(cfg, db, pages, search_html=""):
    cfg["enrich"]["site_search"]["enabled"] = True
    cfg["enrich"]["site_parse"]["enabled"] = True
    return Enricher(cfg, db, http=FakeHttp(pages, search_html))


SEARCH = '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Frusprofile.ru%2Fid%2F1&rut=x">агрегатор</a>' \
         '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fmalyi-podryad.ru%2F&rut=y">сайт</a>'


def test_site_verified_by_inn(cfg, db):
    e = enricher_with_site(cfg, db, {"malyi-podryad.ru": {
        "/": "<html>ООО Ромашка. ИНН 7800000001. <a href='tel:+78121112233'>звоните</a></html>",
        "/contacts": "<html>Почта: <a href='mailto:office@malyi-podryad.ru'>x</a></html>"}}, SEARCH)
    org = e.enrich_one("7800000001")
    assert org.site == "https://malyi-podryad.ru/" and org.site_verified == "inn"
    assert org.phone == "+7 (812) 111-22-33" and org.email == "office@malyi-podryad.ru"
    assert org.phone_unverified is None and org.email_unverified is None


def test_site_verified_by_name(cfg, db):
    db.upsert_org(Org(inn="7800000001", name='ООО "МАЛЫЙ ПОДРЯД"'))
    db.commit()
    e = enricher_with_site(cfg, db, {"malyi-podryad.ru": {"/": "<html>Малый подряд — строим. 8 (812) 222-33-44</html>"}}, SEARCH)
    org = e.enrich_one("7800000001")
    assert org.site_verified == "name" and org.phone == "+7 (812) 222-33-44"


def test_unverified_site_keeps_contacts_separately(cfg, db):
    e = enricher_with_site(cfg, db, {"malyi-podryad.ru": {"/": "<html>Просто сайт. 8 (812) 333-44-55, info@malyi-podryad.ru</html>"}}, SEARCH)
    org = e.enrich_one("7800000001")
    assert org.site == "https://malyi-podryad.ru/" and org.site_verified == "unverified"   # сайт не отброшен
    assert org.phone is None and org.email is None
    assert org.phone_unverified == "+7 (812) 333-44-55" and org.email_unverified == "info@malyi-podryad.ru"
    db.upsert_org(org)
    db.commit()
    assert db.get_org("7800000001").site_verified == "unverified"


def test_directory_site_is_trusted(cfg, db):
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["Название", "ИНН", "Сайт"]); ws.append(["ООО Из справочника", "7800000001", "malyi-podryad.ru"])
    wb.save(resolve_path(cfg, "companies_dir") / "d.xlsx")
    e = enricher_with_site(cfg, db, {"malyi-podryad.ru": {"/": "<html>Ничего общего. 8 (812) 444-55-66</html>"}})
    org = e.enrich_one("7800000001")
    assert org.site_verified == "directory" and org.phone == "+7 (812) 444-55-66"


def test_dadata_site_is_trusted():
    org = Enricher.parse_dadata("7800000001", {"value": "X", "data": {"site": "x.ru", "state": {"status": "ACTIVE"}}})
    assert org.site == "x.ru"
