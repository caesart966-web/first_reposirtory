"""Тесты кросс-сверки и скоринга достоверности."""
from core.config import Config
from core.models import Company, Contact, ContactType, SourceLevel
from core.scoring import merge_and_score, merge_contacts


def _config() -> Config:
    return Config.load()


def _contact(value: str, source: str, level: SourceLevel,
             ctype: ContactType = ContactType.EMAIL, **extra) -> Contact:
    return Contact(type=ctype, value=value, raw=value, source=source,
                   source_url=f"https://{source}.example/", level=level,
                   extra=extra)


class TestMerge:
    def test_same_contact_merged_not_duplicated(self):
        contacts = [
            _contact("info@firma.ru", "zakupki", SourceLevel.A),
            _contact("info@firma.ru", "website", SourceLevel.B),
        ]
        merged = merge_contacts(contacts)
        assert len(merged) == 1
        assert set(merged[0].sources) == {"zakupki", "website"}

    def test_different_contacts_kept(self):
        contacts = [
            _contact("info@firma.ru", "zakupki", SourceLevel.A),
            _contact("sales@firma.ru", "website", SourceLevel.B),
        ]
        assert len(merge_contacts(contacts)) == 2

    def test_case_insensitive_merge(self):
        contacts = [
            _contact("Info@Firma.ru", "zakupki", SourceLevel.A),
            _contact("info@firma.ru", "website", SourceLevel.B),
        ]
        assert len(merge_contacts(contacts)) == 1


class TestScore:
    def test_level_a_scores_40(self):
        company = Company(key="1", inn="7707083893", entity_status="действующее")
        merged = merge_and_score(
            company, [_contact("info@firma.ru", "zakupki", SourceLevel.A)], _config())
        assert merged[0].confidence == 40

    def test_verified_site_plus_corp_domain(self):
        company = Company(key="1", inn="7707083893", website="https://firma.ru",
                          website_verified=True, entity_status="действующее")
        merged = merge_and_score(
            company,
            [_contact("info@firma.ru", "website", SourceLevel.B,
                      site_verified_by_inn=True)],
            _config())
        # +30 (сайт подтверждён) +10 (корп. домен) = 40
        assert merged[0].confidence == 40

    def test_multi_source_bonus(self):
        company = Company(key="1", inn="7707083893", website="https://firma.ru",
                          website_verified=True, entity_status="действующее")
        merged = merge_and_score(
            company,
            [
                _contact("info@firma.ru", "zakupki", SourceLevel.A),
                _contact("info@firma.ru", "website", SourceLevel.B,
                         site_verified_by_inn=True),
            ],
            _config())
        # +40 (A) +30 (сайт) +15 (2 источника) +10 (корп.домен) = 95
        assert merged[0].confidence == 95

    def test_liquidated_penalty(self):
        company = Company(key="1", inn="7707083893", entity_status="ликвидировано")
        merged = merge_and_score(
            company, [_contact("info@firma.ru", "zakupki", SourceLevel.A)], _config())
        assert merged[0].confidence == 10   # 40 - 30

    def test_score_never_negative(self):
        company = Company(key="1", entity_status="ликвидировано")
        merged = merge_and_score(
            company, [_contact("info@firma.ru", "domain_search", SourceLevel.D)],
            _config())
        assert merged[0].confidence == 0

    def test_clamped_at_100(self):
        company = Company(key="1", inn="7707083893", website="https://firma.ru",
                          website_verified=True, entity_status="действующее")
        contacts = [
            _contact("info@firma.ru", "zakupki", SourceLevel.A),
            _contact("info@firma.ru", "sro", SourceLevel.A),
            _contact("info@firma.ru", "website", SourceLevel.B,
                     site_verified_by_inn=True),
            _contact("info@firma.ru", "dgis", SourceLevel.C),
        ]
        merged = merge_and_score(company, contacts, _config())
        assert 0 <= merged[0].confidence <= 100


class TestPrimary:
    def test_corporate_email_primary_over_free(self):
        company = Company(key="1", website="https://firma.ru", website_verified=True,
                          entity_status="действующее")
        contacts = [
            _contact("firma2000@mail.ru", "dgis", SourceLevel.C),
            _contact("info@firma.ru", "dgis", SourceLevel.C),
        ]
        merged = merge_and_score(company, contacts, _config())
        primary = [m for m in merged if m.is_primary and m.type == ContactType.EMAIL]
        assert len(primary) == 1
        assert primary[0].value == "info@firma.ru"

    def test_city_phone_primary_at_equal_confidence(self):
        company = Company(key="1", entity_status="действующее")
        contacts = [
            _contact("+79261112233", "dgis", SourceLevel.C, ctype=ContactType.PHONE),
            _contact("+74951234567", "dgis", SourceLevel.C, ctype=ContactType.PHONE),
        ]
        merged = merge_and_score(company, contacts, _config())
        primary = [m for m in merged if m.is_primary and m.type == ContactType.PHONE]
        assert primary[0].value == "+74951234567"
