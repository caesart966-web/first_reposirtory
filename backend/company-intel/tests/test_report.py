from company_intel.models import Attribute, Profile, Provenance, Query
from company_intel.report import confidence_badge, to_csv, to_markdown, to_text


def profile_with_data() -> Profile:
    profile = Profile(query=Query(name="ООО Ромашка", domain="romashka.ru"))
    profile.attributes = {
        "phone": [Attribute("phone", "+74951203344", 0.87,
                            [Provenance("website", url="https://romashka.ru/contacts",
                                        note="страница: contacts")],
                            {"extension": "210", "label": "fax"})],
        "email": [
            Attribute("email", "info@romashka.ru", 0.92, [Provenance("website")],
                      {"role_account": True}),
            Attribute("email", "i.ivanov@romashka.ru", 0.22,
                      [Provenance("email_guess", note="шаблон для «Иванов Иван»")],
                      {"hypothesis": True}),
            Attribute("email", "shum@nowhere.ru", 0.05, [Provenance("search")], {}),
        ],
        "person": [Attribute("person", "Иванов Иван", 0.7, [Provenance("dadata")],
                             {"position": "директор"})],
    }
    profile.stats = {"findings": 9, "http": {"requests": 4, "cached": 1}, "rounds": 2,
                     "by_source": {"website": 6, "dadata": 3}}
    profile.finished_at = "2026-08-18T13:40:00+00:00"
    return profile


def test_markdown_sections_and_links():
    md = to_markdown(profile_with_data())
    assert "## Телефоны" in md
    assert "+7 (495) 120-33-44 доб. 210 (fax)" in md
    assert "[website](https://romashka.ru/contacts)" in md
    assert "Иванов Иван — директор" in md


def test_markdown_separates_hypotheses():
    md = to_markdown(profile_with_data())
    hypotheses = md.split("## Гипотезы (не подтверждены)")[1]
    assert "i.ivanov@romashka.ru" in hypotheses
    assert "i.ivanov@romashka.ru" not in md.split("## Гипотезы")[0]


def test_low_confidence_noise_is_dropped():
    md = to_markdown(profile_with_data(), min_confidence=0.25)
    assert "shum@nowhere.ru" not in md


def test_csv_columns_and_flags():
    rows = [r.split(";") for r in to_csv(profile_with_data()).strip().splitlines()]
    assert rows[0] == ["kind", "value", "confidence", "hypothesis", "sources", "extra"]
    guessed = [r for r in rows if r[1] == "i.ivanov@romashka.ru"][0]
    assert guessed[3] == "1"


def test_text_marks_hypotheses():
    text = to_text(profile_with_data())
    assert "? i.ivanov@romashka.ru" in text


def test_confidence_badges():
    assert confidence_badge(0.9) == "высокая"
    assert confidence_badge(0.6) == "средняя"
    assert confidence_badge(0.4) == "низкая"
    assert confidence_badge(0.15) == "гипотеза"
