"""Модели данных и слияние результатов из разных источников."""
from __future__ import annotations

from dataclasses import dataclass, field

from .extract import format_phone

# Насколько доверяем источнику. Влияет на итоговую отметку достоверности.
CONF_VERIFIED = "высокая"      # ИНН подтверждён в самом источнике
CONF_PROBABLE = "средняя"      # совпало название/адрес, ИНН явно не виден
CONF_NONE = "нет данных"


@dataclass
class Found:
    """Что удалось вытащить одним источником по одной компании."""

    source: str
    url: str = ""
    inn_confirmed: bool = False
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    site: str = ""
    name: str = ""
    ogrn: str = ""
    kpp: str = ""
    address: str = ""
    director: str = ""
    note: str = ""

    def has_contacts(self) -> bool:
        return bool(self.phones or self.emails or self.site)


@dataclass
class Company:
    """Строка входного файла плюс всё, что по ней нашли."""

    row: int
    name: str
    inn: str
    findings: list[Found] = field(default_factory=list)

    # --- агрегированные поля -------------------------------------------------

    def _accepted(self) -> list[Found]:
        """Находки, которым верим: ИНН подтверждён источником."""
        return [f for f in self.findings if f.inn_confirmed]

    @property
    def phones(self) -> list[str]:
        out: list[str] = []
        for finding in self._accepted():
            for phone in finding.phones:
                if phone not in out:
                    out.append(phone)
        return out

    @property
    def emails(self) -> list[str]:
        out: list[str] = []
        for finding in self._accepted():
            for email in finding.emails:
                if email not in out:
                    out.append(email)
        return out

    @property
    def site(self) -> str:
        for finding in self._accepted():
            if finding.site:
                return finding.site
        return ""

    @property
    def ogrn(self) -> str:
        for finding in self._accepted():
            if finding.ogrn:
                return finding.ogrn
        return ""

    @property
    def address(self) -> str:
        for finding in self._accepted():
            if finding.address:
                return finding.address
        return ""

    @property
    def director(self) -> str:
        for finding in self._accepted():
            if finding.director:
                return finding.director
        return ""

    @property
    def sources(self) -> str:
        seen: list[str] = []
        for finding in self._accepted():
            if finding.has_contacts():
                label = finding.url or finding.source
                if label not in seen:
                    seen.append(label)
        return "; ".join(seen)

    @property
    def confidence(self) -> str:
        if not self.phones and not self.emails:
            return CONF_NONE
        confirming = [f for f in self._accepted() if f.phones or f.emails]
        if len(confirming) >= 2:
            return f"{CONF_VERIFIED} (ИНН подтверждён, источников: {len(confirming)})"
        return f"{CONF_VERIFIED} (ИНН подтверждён)"

    @property
    def phones_display(self) -> str:
        return "; ".join(format_phone(p) for p in self.phones)

    @property
    def rejected_note(self) -> str:
        """Что нашли, но отбросили из-за несовпадения ИНН — для ручной проверки."""
        notes = [
            f"{f.source}: контакты есть, но ИНН на странице не подтверждён"
            for f in self.findings
            if not f.inn_confirmed and f.has_contacts()
        ]
        return "; ".join(notes)
