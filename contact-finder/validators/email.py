"""Валидация e-mail: синтаксис (RFC-подобный), MX-запись, стоп-листы, скоринг типа.

MX-проверка выполняется реальным DNS-запросом (dnspython) и кэшируется на время
прогона. В тестах и офлайн-режиме отключается флагом check_mx=False.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Iterable, Optional

from utils.obfuscation import deobfuscate_text

# Практичный RFC-5322-подобный шаблон + кириллические домены (.рф)
EMAIL_RE = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.\-]{1,64}"
    r"@"
    r"(?:[A-Za-z0-9а-яёА-ЯЁ](?:[A-Za-z0-9а-яёА-ЯЁ\-]{0,61}[A-Za-z0-9а-яёА-ЯЁ])?\.)+"
    r"(?:[A-Za-zрфРФ]{2,24})",
    re.UNICODE,
)

_SYNTAX_FULL_RE = re.compile(r"^%s$" % EMAIL_RE.pattern, re.UNICODE)

# Расширения файлов, которые часто ловятся как «домены» из имён файлов (logo@2x.png)
_FILE_EXT_TAILS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "css", "js", "ico", "pdf", "webm",
}


@dataclass
class EmailVerdict:
    """Итог проверки одного адреса."""

    email: str                      # нормализованный (lower)
    valid: bool
    reason: str = ""
    is_free_mail: bool = False      # бесплатная почта (mail.ru, gmail...)
    is_corporate: bool = False      # домен совпадает с сайтом компании
    mx_checked: bool = False
    mx_ok: Optional[bool] = None


@dataclass
class EmailValidator:
    """Проверяет адреса с учётом стоп-листов из config.yaml."""

    stop_prefixes: list[str] = field(default_factory=list)
    stop_addresses: list[str] = field(default_factory=list)
    dev_domains: list[str] = field(default_factory=list)
    free_domains: list[str] = field(default_factory=list)
    check_mx: bool = True
    mx_timeout: float = 5.0
    _mx_cache: dict[str, Optional[bool]] = field(default_factory=dict)

    # --- синхронная часть (без сети) -------------------------------------

    def syntax_ok(self, email: str) -> bool:
        email = (email or "").strip()
        if not email or ".." in email or email.startswith(".") or "@." in email:
            return False
        if not _SYNTAX_FULL_RE.match(email):
            return False
        local, _, domain = email.partition("@")
        if local.endswith(".") or len(domain) > 253:
            return False
        tail = domain.rsplit(".", 1)[-1].lower()
        if tail in _FILE_EXT_TAILS:
            return False
        return True

    def _stoplisted(self, email: str) -> Optional[str]:
        local, _, domain = email.partition("@")
        local_l, domain_l = local.lower(), domain.lower()
        if email.lower() in (a.lower() for a in self.stop_addresses):
            return "адрес из шаблона/примера"
        for prefix in self.stop_prefixes:
            p = prefix.lower().rstrip("@")
            if local_l == p or local_l.startswith(p + ".") or local_l.startswith(p + "-"):
                return f"служебный/шаблонный адрес ({prefix})"
        if any(ch in "аеиоуыэюяё" for ch in local_l) and "собака" in local_l:
            return "обфусцированный мусор"
        if domain_l in ("example.com", "example.org", "example.ru", "site.ru",
                        "domain.ru", "domain.com", "test.ru", "email.ru", "почта.рф"):
            return "домен-заглушка"
        for dev in self.dev_domains:
            d = dev.lower()
            if domain_l == d or domain_l.endswith("." + d):
                return f"почта веб-студии/хостера ({dev})"
        return None

    def classify(self, email: str, company_site_domain: Optional[str] = None) -> EmailVerdict:
        """Синтаксис + стоп-листы + тип (без DNS)."""
        email = (email or "").strip().strip(".,;:()<>[]").lower()
        if not self.syntax_ok(email):
            return EmailVerdict(email=email, valid=False, reason="не проходит синтаксис RFC")
        stop_reason = self._stoplisted(email)
        if stop_reason:
            return EmailVerdict(email=email, valid=False, reason=stop_reason)
        domain = email.partition("@")[2].lower()
        is_free = any(domain == d.lower() for d in self.free_domains)
        is_corp = False
        if company_site_domain:
            site = company_site_domain.lower().removeprefix("www.")
            is_corp = domain == site or domain.endswith("." + site)
        return EmailVerdict(email=email, valid=True, is_free_mail=is_free, is_corporate=is_corp)

    # --- MX-проверка (сеть) ----------------------------------------------

    async def mx_ok(self, domain: str) -> Optional[bool]:
        """True/False — есть ли у домена MX (или A как fallback); None — DNS недоступен."""
        domain = domain.lower()
        if domain in self._mx_cache:
            return self._mx_cache[domain]
        result: Optional[bool]
        try:
            import dns.asyncresolver
            import dns.exception

            resolver = dns.asyncresolver.Resolver()
            resolver.lifetime = self.mx_timeout
            try:
                answers = await resolver.resolve(domain, "MX")
                result = len(list(answers)) > 0
            except (dns.exception.DNSException, OSError):
                # RFC 5321: при отсутствии MX почта может ходить по A-записи
                try:
                    answers = await resolver.resolve(domain, "A")
                    result = len(list(answers)) > 0
                except (dns.exception.DNSException, OSError):
                    result = False
        except ImportError:
            result = None
        except (asyncio.TimeoutError, Exception):
            result = None
        self._mx_cache[domain] = result
        return result

    async def validate(self, email: str,
                       company_site_domain: Optional[str] = None) -> EmailVerdict:
        """Полная проверка: синтаксис, стоп-листы, MX."""
        verdict = self.classify(email, company_site_domain)
        if not verdict.valid or not self.check_mx:
            return verdict
        domain = verdict.email.partition("@")[2]
        mx = await self.mx_ok(domain)
        verdict.mx_checked = mx is not None
        verdict.mx_ok = mx
        if mx is False:
            verdict.valid = False
            verdict.reason = "у домена нет MX/A-записи (почта не принимается)"
        return verdict


def extract_emails(text: str) -> list[str]:
    """Найти все адреса в тексте, включая обфусцированные. Без дубликатов."""
    if not text:
        return []
    prepared = deobfuscate_text(text)
    found: list[str] = []
    seen: set[str] = set()
    for match in EMAIL_RE.finditer(prepared):
        email = match.group(0).strip(".,;:()<>[]").lower()
        if email not in seen:
            seen.add(email)
            found.append(email)
    return found


def domain_of(email_or_url: str) -> str:
    """Домен адреса почты или URL (без www)."""
    value = (email_or_url or "").strip().lower()
    if "@" in value:
        return value.rpartition("@")[2]
    value = re.sub(r"^[a-z+]+://", "", value)
    value = value.split("/", 1)[0].split(":", 1)[0]
    return value.removeprefix("www.")


def dedupe_keep_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
