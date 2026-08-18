from company_intel.merge import apply_relevance, drop_below, merge_findings, noisy_or
from company_intel.models import Finding, Provenance, Query


def f(kind, value, source, confidence, url=None, **extra):
    return Finding(kind, value, Provenance(source, url=url), confidence, extra)


def test_noisy_or_combines_independent_sources():
    assert round(noisy_or([0.6, 0.6]), 3) == 0.84
    assert noisy_or([]) == 0.0


def test_same_value_from_two_sources_beats_single_source():
    two = merge_findings([
        f("phone", "+74951203344", "website", 0.7),
        f("phone", "+74951203344", "2gis", 0.7),
    ])["phone"][0]
    one = merge_findings([f("phone", "+79991112233", "website", 0.7)])["phone"][0]
    assert two.confidence > one.confidence
    assert set(two.source_names) == {"website", "2gis"}


def test_repeats_inside_one_source_add_little():
    attr = merge_findings([
        f("email", "info@x.ru", "website", 0.7, url="https://x.ru/"),
        f("email", "info@x.ru", "website", 0.7, url="https://x.ru/contacts"),
        f("email", "info@x.ru", "website", 0.7, url="https://x.ru/about"),
    ])["email"][0]
    assert 0.7 < attr.confidence <= 0.75
    assert len(attr.sources) == 3


def test_confidence_never_reaches_one():
    attr = merge_findings([f("inn", "7707083893", f"src{i}", 0.9) for i in range(8)])["inn"][0]
    assert attr.confidence <= 0.99


def test_names_deduplicate_by_legal_form():
    attrs = merge_findings([
        f("name", 'ООО "Ромашка-Строй"', "dadata", 0.9),
        f("name", "Ромашка-Строй", "website", 0.5),
    ])
    assert len(attrs["name"]) == 1
    assert attrs["name"][0].value == 'ООО "Ромашка-Строй"'   # побеждает более уверенный


def test_relevance_marks_foreign_and_corporate_mail():
    attrs = merge_findings([
        f("email", "info@romashka.ru", "website", 0.7),
        f("email", "dev@webstudio.ru", "website", 0.7),
        f("email", "romashka@mail.ru", "search", 0.7),
    ])
    notes = apply_relevance(attrs, Query(domain="romashka.ru"))
    by_value = {a.value: a for a in attrs["email"]}
    assert by_value["info@romashka.ru"].extra["corporate"] is True
    assert by_value["dev@webstudio.ru"].extra["foreign_domain"] is True
    assert by_value["romashka@mail.ru"].extra["mail_provider"] == "freemail"
    assert by_value["info@romashka.ru"].confidence > by_value["dev@webstudio.ru"].confidence
    assert any("webstudio.ru" in n for n in notes)


def test_drop_below():
    attrs = merge_findings([
        f("email", "a@x.ru", "website", 0.8),
        f("email", "b@x.ru", "search", 0.2),
    ])
    assert len(drop_below(attrs, 0.5)["email"]) == 1
