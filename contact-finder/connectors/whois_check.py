"""WHOIS-сопоставление домена (вспомогательный модуль для поиска домена).

Для зон .ru/.su/.рф регистратура ТЦИ отдаёт поле org: с наименованием
владельца-юрлица. Совпадение org с названием компании — дополнительный
сигнал при верификации домена (но не замена проверке ИНН на сайте).
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Optional

_TCI_HOST = "whois.tcinet.ru"
_TCI_ZONES = (".ru", ".su", ".рф", ".xn--p1ai")
_WHOIS_PORT = 43
_TIMEOUT = 10.0


@dataclass
class WhoisInfo:
    """Выжимка из WHOIS-ответа."""

    domain: str
    org: Optional[str] = None
    registrar: Optional[str] = None
    created: Optional[str] = None
    raw: str = ""

    @property
    def found(self) -> bool:
        return bool(self.org or self.registrar or self.created)


def _extract_field(raw: str, field_name: str) -> Optional[str]:
    m = re.search(rf"^{field_name}:\s*(.+)$", raw, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


async def whois_lookup(domain: str) -> Optional[WhoisInfo]:
    """Запросить WHOIS для домена .ru/.su/.рф. None — зона не поддерживается/ошибка."""
    domain = (domain or "").strip().lower().removeprefix("www.")
    if not domain or not domain.endswith(_TCI_ZONES):
        return None
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(_TCI_HOST, _WHOIS_PORT), timeout=_TIMEOUT)
        writer.write((domain + "\r\n").encode("idna" if domain.isascii() else "utf-8"))
        await writer.drain()
        chunks: list[bytes] = []
        while True:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=_TIMEOUT)
            if not chunk:
                break
            chunks.append(chunk)
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass
    except (asyncio.TimeoutError, ConnectionError, OSError, UnicodeError):
        return None

    raw = b"".join(chunks).decode("utf-8", errors="replace")
    return WhoisInfo(
        domain=domain,
        org=_extract_field(raw, "org"),
        registrar=_extract_field(raw, "registrar"),
        created=_extract_field(raw, "created"),
        raw=raw,
    )


def org_matches_company(info: Optional[WhoisInfo], company_name: Optional[str]) -> bool:
    """Похоже ли поле org из WHOIS на название компании (грубое сравнение)."""
    if info is None or not info.org or not company_name:
        return False
    org_tokens = set(re.findall(r"[a-zа-яё\d]{3,}", info.org.lower()))
    name_tokens = set(re.findall(r"[a-zа-яё\d]{3,}", company_name.lower()))
    stop = {"ооо", "llc", "ltd", "jsc", "оао", "зао", "пао", "company", "limited"}
    org_tokens -= stop
    name_tokens -= stop
    if not org_tokens or not name_tokens:
        return False
    return bool(org_tokens & name_tokens)
