"""Уровень A. Открытые реестры СРО: НОСТРОЙ (строители) и НОПРИЗ (проектировщики).

Оба национальных объединения публикуют открытые API единого реестра членов.
Ответы полуструктурированные, поэтому контакты (телефон/почта) достаём обходом
JSON по значениям, а не по жёсткой схеме — API переживает смену полей.
"""
from __future__ import annotations

from typing import Any, Optional

from connectors.base import BaseConnector, register_connector, walk_json_for_strings
from core.models import Company, ConnectorResult, Contact, ContactType, SourceLevel
from utils.http import FetchError
from validators.email import extract_emails
from validators.phone import extract_phones

_REGISTRIES = [
    {
        "name": "НОСТРОЙ",
        "url": "https://api-open.nostroy.ru/api/sro/all/member/list",
        "public_url": "https://reestr.nostroy.ru/",
    },
    {
        "name": "НОПРИЗ",
        "url": "https://reestr.nopriz.ru/api/sro/all/member/list",
        "public_url": "https://reestr.nopriz.ru/",
    },
]


@register_connector
class SroConnector(BaseConnector):
    """Единые реестры членов СРО (НОСТРОЙ/НОПРИЗ)."""

    name = "sro"
    title = "Реестры СРО"
    level = SourceLevel.A
    default_priority = 30

    def can_run(self, company: Company) -> bool:
        return bool(company.inn)

    async def fetch(self, company: Company) -> ConnectorResult:
        assert company.inn is not None
        contacts: list[Contact] = []
        updates: dict[str, Any] = {}
        urls: list[str] = []
        errors: list[str] = []

        for registry in _REGISTRIES:
            try:
                member = await self._find_member(registry, company.inn)
            except FetchError as exc:
                errors.append(f"{registry['name']}: {exc}")
                continue
            if member is None:
                continue
            urls.append(registry["public_url"])
            contacts.extend(self._contacts_from_member(member, registry))
            self._updates_from_member(member, updates)

        if not contacts and not updates:
            error = "; ".join(errors) if errors else "компания не состоит в СРО"
            # Ошибки обоих реестров считаем временными только если оба упали
            retry = len(errors) == len(_REGISTRIES) and bool(errors)
            if retry:
                return ConnectorResult.failed(error, retry_later=True)
            return ConnectorResult(ok=True, error=error)
        return ConnectorResult(contacts=contacts, company_updates=updates,
                               source_urls=urls)

    # ------------------------------------------------------------------ #

    async def _find_member(self, registry: dict, inn: str) -> Optional[dict]:
        resp = await self.http.fetch(
            registry["url"], method="POST",
            json_body={
                "filters": {"inn": inn},
                "page": 1,
                "pageCount": 5,
                "searchString": inn,
            },
            headers={"Accept": "application/json",
                     "Content-Type": "application/json"},
            use_cache=True,
        )
        if resp.status in (403, 451):
            raise FetchError(f"{registry['name']} закрыл открытый API (HTTP {resp.status})",
                             url=registry["url"], status=resp.status)
        if not resp.ok:
            raise FetchError(f"{registry['name']} вернул HTTP {resp.status}",
                             url=registry["url"], status=resp.status,
                             retry_later=resp.status >= 500 or resp.status == 429)
        try:
            payload = resp.json()
        except ValueError:
            raise FetchError(f"{registry['name']}: ответ не JSON", url=registry["url"])

        rows = self._member_rows(payload)
        for row in rows:
            row_inn = str(row.get("inn") or row.get("Inn") or "").strip()
            if row_inn == inn:
                return row
        return rows[0] if len(rows) == 1 else None

    @staticmethod
    def _member_rows(payload: Any) -> list[dict]:
        """Достать список членов из вариантов обёрток {data:{data:[...]}} и т.п."""
        node = payload
        for _ in range(3):
            if isinstance(node, dict):
                for key in ("data", "items", "list", "result", "rows"):
                    if key in node:
                        node = node[key]
                        break
                else:
                    break
            if isinstance(node, list):
                return [r for r in node if isinstance(r, dict)]
        return []

    def _contacts_from_member(self, member: dict, registry: dict) -> list[Contact]:
        contacts: list[Contact] = []
        seen: set[tuple[str, str]] = set()
        for path, value in walk_json_for_strings(member):
            path_l = path.lower()
            is_contact_field = any(k in path_l for k in ("phone", "email", "contact", "телефон", "почта"))
            for email in extract_emails(value):
                key = ("email", email)
                if key not in seen:
                    seen.add(key)
                    contacts.append(Contact(
                        type=ContactType.EMAIL, value=email, raw=value[:200],
                        source=self.name, source_url=registry["public_url"],
                        level=self.level,
                        extra={"registry": registry["name"], "field": path},
                    ))
            # телефоны берём либо из явных контактных полей, либо из строк с "+7"
            if is_contact_field or "+7" in value or value.startswith("8 ("):
                for phone in extract_phones(value):
                    key = ("phone", phone)
                    if key not in seen:
                        seen.add(key)
                        contacts.append(Contact(
                            type=ContactType.PHONE, value=phone, raw=value[:200],
                            source=self.name, source_url=registry["public_url"],
                            level=self.level,
                            extra={"registry": registry["name"], "field": path},
                        ))
        return contacts

    @staticmethod
    def _updates_from_member(member: dict, updates: dict[str, Any]) -> None:
        director = member.get("director") or member.get("head") or member.get("fio")
        if isinstance(director, str) and director.strip() and "director_name" not in updates:
            updates["director_name"] = director.strip().title()
        full = member.get("full_description") or member.get("fullName") or member.get("full_name")
        if isinstance(full, str) and full.strip() and "name_full" not in updates:
            updates["name_full"] = full.strip()
        short = member.get("short_description") or member.get("shortName") or member.get("short_name")
        if isinstance(short, str) and short.strip() and "name_short" not in updates:
            updates["name_short"] = short.strip()
        ogrn = member.get("ogrn") or member.get("Ogrn")
        if isinstance(ogrn, (str, int)) and str(ogrn).strip() and "ogrn" not in updates:
            updates["ogrn"] = str(ogrn).strip()
