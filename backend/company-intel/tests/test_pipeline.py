import pytest

from company_intel.config import Config
from company_intel.models import Query
from company_intel.pipeline import run_pipeline, seed_findings

from fake_fetcher import FakeFetcher

SITE = "https://romashka-stroy.ru"


def site_routes(fixtures) -> dict[str, str]:
    return {
        f"{SITE}/": (fixtures / "company_home.html").read_text(encoding="utf-8"),
        f"{SITE}/contacts": (fixtures / "company_site.html").read_text(encoding="utf-8"),
        f"{SITE}/about": (fixtures / "company_about.html").read_text(encoding="utf-8"),
    }


def website_only(**kwargs) -> Config:
    return Config.from_env(enabled_sources=["website"], cache_path=None, **kwargs)


def test_seed_validates_input():
    query = Query(inn="7707083894", ogrn="1027700132195", domain="HTTPS://WWW.Romashka.ru/")
    findings, warnings = seed_findings(query)
    kinds = {f.kind for f in findings}
    assert "ogrn" in kinds and "domain" in kinds
    assert "inn" not in kinds                       # контрольная сумма не сошлась
    assert any("ИНН" in w for w in warnings)
    assert query.domain == "romashka.ru"


def test_domain_derived_from_email():
    query = Query(email="info@romashka-stroy.ru")
    seed_findings(query)
    assert query.domain == "romashka-stroy.ru"


def test_freemail_does_not_become_company_domain():
    query = Query(email="romashka@mail.ru")
    seed_findings(query)
    assert query.domain is None


async def test_full_run_over_fake_site(fixtures):
    fetcher = FakeFetcher(site_routes(fixtures))
    profile = await run_pipeline(
        Query(name='ООО "Ромашка-Строй"', domain="romashka-stroy.ru"),
        website_only(), fetcher=fetcher,
    )
    emails = profile.values("email", 0.3)
    assert "info@romashka-stroy.ru" in emails
    assert "zakupki@romashka-stroy.ru" in emails
    assert "+74951203344" in profile.values("phone", 0.3)
    assert "7707083893" in profile.values("inn")
    assert "1027700132195" in profile.values("ogrn")
    assert any("Иванов Сергей Петрович" == p for p in profile.values("person", 0.3))
    assert "https://t.me/romashkastroy" in profile.values("social", 0.3)
    assert profile.stats["findings"] > 20


async def test_contractor_email_ranked_below_corporate(fixtures):
    fetcher = FakeFetcher(site_routes(fixtures))
    profile = await run_pipeline(
        Query(domain="romashka-stroy.ru"), website_only(), fetcher=fetcher,
    )
    ranked = {a.value: a.confidence for a in profile.get("email")}
    assert ranked["info@romashka-stroy.ru"] > ranked["dev@webstudio-x.ru"]


async def test_pipeline_unrolls_from_email_only(fixtures):
    """Знаем только почту → выводится домен → обходится сайт → находятся реквизиты."""
    fetcher = FakeFetcher(site_routes(fixtures))
    profile = await run_pipeline(
        Query(email="info@romashka-stroy.ru"), website_only(), fetcher=fetcher,
    )
    assert "7707083893" in profile.values("inn")
    assert "+78002001590" in profile.values("phone", 0.3)


async def test_source_failure_does_not_break_run(fixtures, monkeypatch):
    from company_intel.sources.website import WebsiteSource

    async def boom(self, ctx):
        raise RuntimeError("источник сломался")

    monkeypatch.setattr(WebsiteSource, "run", boom)
    profile = await run_pipeline(
        Query(domain="romashka-stroy.ru"), website_only(),
        fetcher=FakeFetcher(site_routes(fixtures)),
    )
    assert any("website" in w for w in profile.warnings)
    assert profile.finished_at is not None


async def test_empty_query_returns_warning():
    profile = await run_pipeline(Query(), website_only(), fetcher=FakeFetcher({}))
    assert profile.warnings
    assert profile.attributes == {}


async def test_hypotheses_are_flagged_and_low(fixtures):
    config = Config.from_env(enabled_sources=["website", "email_guess"],
                             cache_path=None, allow_email_guessing=True)
    profile = await run_pipeline(
        Query(domain="romashka-stroy.ru"), config, fetcher=FakeFetcher(site_routes(fixtures)),
    )
    guessed = [a for a in profile.get("email") if a.extra.get("hypothesis")]
    assert guessed, "гипотезы должны появиться при --guess-emails"
    assert all(a.confidence < 0.3 for a in guessed)
    real = [a for a in profile.get("email") if not a.extra.get("hypothesis")]
    assert max(a.confidence for a in real) > max(a.confidence for a in guessed)


async def test_confirmed_guess_stops_being_a_hypothesis(fixtures):
    """Угаданный адрес, найденный на сайте, перестаёт быть гипотезой."""
    config = Config.from_env(enabled_sources=["website", "email_guess"],
                             cache_path=None, allow_email_guessing=True)
    profile = await run_pipeline(
        Query(domain="romashka-stroy.ru"), config, fetcher=FakeFetcher(site_routes(fixtures)),
    )
    petrova = next(a for a in profile.get("email") if a.value == "m.petrova@romashka-stroy.ru")
    assert not petrova.extra.get("hypothesis")
    assert petrova.extra.get("guess_confirmed") is True
    assert petrova.confidence > 0.5


async def test_crawler_follows_second_level_links(fixtures):
    """«Реквизиты» есть только в шапке страницы контактов — обход должен дойти туда."""
    routes = site_routes(fixtures)
    routes[f"{SITE}/rekvizity"] = (
        "<html><head><meta charset='utf-8'><title>Реквизиты</title></head>"
        "<body><p>ОГРН 1027700132195, ИНН 7707083893, тел. +7 495 999-88-77</p></body></html>"
    )
    fetcher = FakeFetcher(routes)
    profile = await run_pipeline(
        Query(domain="romashka-stroy.ru"), website_only(), fetcher=fetcher,
    )
    assert f"{SITE}/rekvizity" in fetcher.seen
    assert "+74959998877" in profile.values("phone", 0.3)


async def test_page_budget_is_respected(fixtures):
    fetcher = FakeFetcher(site_routes(fixtures))
    await run_pipeline(
        Query(domain="romashka-stroy.ru"), website_only(max_pages_per_site=2), fetcher=fetcher,
    )
    fetched_ok = [u for u in fetcher.seen if u in site_routes(fixtures)]
    assert len(fetched_ok) <= 2
