import json

import pytest

from company_intel.config import Config
from company_intel.models import Query
from company_intel.sources import Context, available_sources, describe_sources
from company_intel.sources.crtsh import CrtShSource
from company_intel.sources.dadata import DaDataSource
from company_intel.sources.hunter import HunterSource
from company_intel.sources.rdap import RdapSource
from company_intel.sources.search import SearchSource, parse_yandex_xml
from company_intel.sources.website import WebsiteSource, _page_kind

from fake_fetcher import FakeFetcher


def ctx_for(query: Query, config: Config, fetcher) -> Context:
    return Context(query=query, config=config, fetcher=fetcher)


def test_registry_reports_missing_keys():
    config = Config.from_env()
    rows = {r["name"]: r for r in describe_sources(config)}
    assert rows["dadata"]["ready"] is False
    assert "DADATA_TOKEN" in rows["dadata"]["reason"]
    assert rows["website"]["ready"] is True


def test_disabled_sources_are_filtered():
    config = Config.from_env(disabled_sources=["website"])
    ready, skipped = available_sources(config)
    assert "website" not in [s.name for s in ready]
    assert ("website", "отключён настройками") in skipped


def test_enabled_sources_whitelist():
    ready, _ = available_sources(Config.from_env(enabled_sources=["website", "dns"]))
    assert {s.name for s in ready} == {"website", "dns"}


async def test_dadata_parses_party(fixtures):
    payload = json.loads((fixtures / "dadata_party.json").read_text(encoding="utf-8"))
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
    fetcher = FakeFetcher({}, {url: payload})
    config = Config.from_env()
    config.keys["DADATA_TOKEN"] = "test-token"
    findings = await DaDataSource().run(ctx_for(Query(inn="7707083893"), config, fetcher))
    by_kind = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f.value)
    assert "7707083893" in by_kind["inn"]
    assert "1027700132195" in by_kind["ogrn"]
    assert any("Егорова" in a for a in by_kind["address"])
    assert "Иванов Сергей Петрович" in by_kind["person"]
    assert any("ACTIVE" in f for f in by_kind["fact"])
    assert "info@romashka-stroy.ru" in by_kind["email"]
    assert all(f.confidence >= 0.9 for f in findings if f.kind == "inn")


async def test_crtsh_collects_subdomains_of_same_root():
    url = "https://crt.sh/"
    payload = [
        {"name_value": "romashka-stroy.ru\nwww.romashka-stroy.ru"},
        {"name_value": "*.mail.romashka-stroy.ru"},
        {"name_value": "other-company.ru"},
    ]
    fetcher = FakeFetcher({}, {url: payload})
    findings = await CrtShSource().run(
        ctx_for(Query(domain="romashka-stroy.ru"), Config.from_env(), fetcher)
    )
    values = {f.value for f in findings}
    assert "mail.romashka-stroy.ru" in values
    assert "romashka-stroy.ru" in values
    assert "other-company.ru" not in values


async def test_rdap_extracts_registrar_and_contacts():
    url = "https://rdap.org/domain/romashka-stroy.com"
    payload = {
        "events": [{"eventAction": "registration", "eventDate": "2005-03-14T10:00:00Z"}],
        "entities": [
            {"roles": ["registrar"], "vcardArray": ["vcard", [["fn", {}, "text", "RU-CENTER"]]]},
            {"roles": ["registrant"], "vcardArray": ["vcard", [
                ["fn", {}, "text", "Romashka Stroy LLC"],
                ["email", {}, "text", "admin@romashka-stroy.com"],
                ["tel", {}, "text", "+7.4951203344"]]]},
            {"roles": ["abuse"], "vcardArray": ["vcard", [
                ["email", {}, "text", "abuse@registrar.example"]]]},
        ],
    }
    fetcher = FakeFetcher({}, {url: payload})
    findings = await RdapSource().run(
        ctx_for(Query(domain="romashka-stroy.com"), Config.from_env(), fetcher)
    )
    facts = [f.value for f in findings if f.kind == "fact"]
    assert any("RU-CENTER" in f for f in facts)
    assert any("2005-03-14" in f for f in facts)
    emails = {f.value: f.confidence for f in findings if f.kind == "email"}
    assert emails["admin@romashka-stroy.com"] > emails["abuse@registrar.example"]


async def test_hunter_maps_confidence():
    url = "https://api.hunter.io/v2/domain-search"
    payload = {"data": {"organization": "Romashka Stroy", "pattern": "{f}.{last}",
                        "emails": [
                            {"value": "s.ivanov@romashka-stroy.ru", "confidence": 95,
                             "first_name": "Сергей", "last_name": "Иванов",
                             "position": "CEO", "type": "personal"},
                            {"value": "info@romashka-stroy.ru", "confidence": 20,
                             "type": "generic"}]}}
    fetcher = FakeFetcher({}, {url: payload})
    config = Config.from_env()
    config.keys["HUNTER_API_KEY"] = "test"
    findings = await HunterSource().run(
        ctx_for(Query(domain="romashka-stroy.ru"), config, fetcher)
    )
    emails = {f.value: f.confidence for f in findings if f.kind == "email"}
    assert emails["s.ivanov@romashka-stroy.ru"] > emails["info@romashka-stroy.ru"]
    assert any(f.kind == "person" and f.value == "Сергей Иванов" for f in findings)


def test_yandex_xml_parsing():
    xml = """<?xml version="1.0" encoding="utf-8"?><yandexsearch><response><results>
    <grouping><group><doc><url>https://rusprofile.ru/id/1</url>
    <title>ООО <hlword>Ромашка</hlword></title>
    <passages><passage>ИНН 7707083893</passage></passages></doc></group></grouping>
    </results></response></yandexsearch>"""
    hits = parse_yandex_xml(xml)
    assert hits[0].url == "https://rusprofile.ru/id/1"
    assert "Ромашка" in hits[0].title
    assert "7707083893" in hits[0].snippet
    assert parse_yandex_xml("не xml") == []


def test_search_requires_any_engine_key():
    ok, reason = SearchSource().available(Config.from_env())
    assert not ok and "SerpApi" in reason
    config = Config.from_env()
    config.keys["BRAVE_API_KEY"] = "x"
    assert SearchSource().available(config)[0] is True


def test_search_relevance_filter():
    source = SearchSource()
    config = Config.from_env()
    ctx = ctx_for(Query(name='ООО "Ромашка-Строй"', inn="7707083893"), config, FakeFetcher({}))
    assert source._page_mentions_company(ctx, "Компания ромашка-строй, отзывы")
    assert source._page_mentions_company(ctx, "ИНН 7707083893 в реестре")
    assert not source._page_mentions_company(ctx, "Совершенно другая страница про котиков")


@pytest.mark.parametrize("url,kind", [
    ("https://x.ru/", "home"),
    ("https://x.ru/kontakty/", "contacts"),
    ("https://x.ru/rekvizity", "requisites"),
    ("https://x.ru/about-us", "about"),
    ("https://x.ru/blog/post-1", "other"),
])
def test_page_kind(url, kind):
    assert _page_kind(url) == kind


def test_website_link_ranking():
    links = [
        "https://x.ru/blog/2024/01/post",
        "https://x.ru/contacts",
        "https://x.ru/o-kompanii",
        "https://x.ru/price.pdf",
    ]
    ranked = WebsiteSource()._rank_links(links, "x.ru")
    assert ranked[0] == "https://x.ru/contacts"
    assert "https://x.ru/price.pdf" not in ranked
