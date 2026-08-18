"""Извлечение контактов и реквизитов из HTML и текста.

Здесь только «сырое» распознавание: что похоже на почту/телефон/ИНН. Решение,
верить ли находке, принимается позже — в `merge.py` по количеству и качеству
источников.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit, unquote

from .normalize import (
    EMAIL_RE, deobfuscate, normalize_email, normalize_phone, phone_extension,
    normalize_domain, validate_inn, validate_ogrn, validate_kpp,
)

try:  # bs4 нужен только для HTML; текстовые функции работают и без него
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore


# --- телефоны --------------------------------------------------------------

# Кандидат: 8+ цифр вперемешку с разделителями. Отсев — в normalize_phone.
_PHONE_CANDIDATE = re.compile(r"(?<![\w])(\+?\d[\d\-\s()\.]{7,22}\d)(?![\w])")
# Контекст, после которого цифры — это точно не телефон.
_NOT_PHONE_BEFORE = re.compile(
    r"(?:\b(?:инн|кпп|огрн|огрнип|окпо|окато|октмо|бик|счет|счёт|account|iban|"
    r"swift|индекс|артикул|заказ|серия|паспорт|лиценз\w*|свидетельств\w*|гост|"
    r"снип|версия|version|isbn|№)"
    r"|(?<![\wа-яё])[рк]/с)"
    r"\s*[:№#]?\s*$",
    re.I,
)
# Подпись перед номером: помечаем факс/мобильный/мессенджер, чтобы не путать с офисом.
_PHONE_LABEL_BEFORE = re.compile(
    r"\b(факс|fax|моб\w*|mobile|cell|whatsapp|ватсап|viber|вайбер|telegram|"
    r"телеграм|тел\w*|phone|бесплатн\w*|горячая\s+лини\w*|8-?800)"
    r"[\s.:—–-]*$",
    re.I,
)
_LABEL_MAP = {
    "факс": "fax", "fax": "fax", "whatsapp": "whatsapp", "ватсап": "whatsapp",
    "viber": "viber", "вайбер": "viber", "telegram": "telegram", "телеграм": "telegram",
}

_DATE_LIKE = re.compile(r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b")


def phone_label(before: str) -> str | None:
    """Определяет тип номера по подписи слева: факс, мобильный, мессенджер."""
    m = _PHONE_LABEL_BEFORE.search(before or "")
    if not m:
        return None
    word = m.group(1).lower()
    for key, label in _LABEL_MAP.items():
        if word.startswith(key):
            return label
    if word.startswith(("моб", "mobile", "cell")):
        return "mobile"
    if word.startswith(("бесплатн", "горячая", "8-800", "8800")):
        return "tollfree"
    return None


def extract_phones(text: str, country: str = "ru") -> list[tuple[str, str | None, str | None]]:
    """Возвращает [(E.164, добавочный|None, метка|None)] в порядке появления."""
    if not text:
        return []
    out: list[tuple[str, str | None, str | None]] = []
    seen: set[str] = set()
    for m in _PHONE_CANDIDATE.finditer(text):
        raw = m.group(1)
        if _DATE_LIKE.search(raw):
            continue
        before = text[max(0, m.start() - 24):m.start()]
        if _NOT_PHONE_BEFORE.search(before):
            continue
        digits = re.sub(r"\D", "", raw)
        if country == "ru" and len(digits) not in (10, 11) and not raw.strip().startswith("+"):
            continue
        phone = normalize_phone(raw, country)
        if not phone or phone in seen:
            continue
        seen.add(phone)
        tail = text[m.end():m.end() + 40]
        out.append((phone, phone_extension(tail), phone_label(before)))
    return out


# --- почта -----------------------------------------------------------------

def extract_emails(text: str) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for candidate in EMAIL_RE.findall(deobfuscate(text)):
        email = normalize_email(candidate)
        if email and email not in seen:
            seen.add(email)
            out.append(email)
    return out


# --- реквизиты -------------------------------------------------------------

_INN_RE = re.compile(r"\bИНН[\s:№/]*(\d{10}|\d{12})\b", re.I)
_OGRN_RE = re.compile(r"\bОГРН(?:ИП)?[\s:№/]*(\d{13}|\d{15})\b", re.I)
_KPP_RE = re.compile(r"\bКПП[\s:№/]*(\d{4}[\dA-ZА-Я]{2}\d{3})\b", re.I)
_OKPO_RE = re.compile(r"\bОКПО[\s:№/]*(\d{8}|\d{10})\b", re.I)


def extract_requisites(text: str) -> dict[str, list[str]]:
    """ИНН/ОГРН/КПП/ОКПО с проверкой контрольных сумм там, где они есть."""
    if not text:
        return {}
    found: dict[str, list[str]] = {}

    def add(kind: str, value: str) -> None:
        found.setdefault(kind, [])
        if value not in found[kind]:
            found[kind].append(value)

    for value in _INN_RE.findall(text):
        if validate_inn(value):
            add("inn", value)
    for value in _OGRN_RE.findall(text):
        if validate_ogrn(value):
            add("ogrn", value)
    for value in _KPP_RE.findall(text):
        if validate_kpp(value):
            add("kpp", value.upper())
    for value in _OKPO_RE.findall(text):
        add("okpo", value)
    return found


# --- адреса ----------------------------------------------------------------

_ADDR_RE = re.compile(
    r"(?:\b\d{6}\b[,\s]{1,3})?"
    r"(?:(?:г\.|г\s|город|обл\.|область|респ\.|край|пос\.|пгт|с\.|дер\.)[^\n;|]{2,80})?"
    r"(?:ул\.|улица|просп\.|проспект|пр-?кт|пер\.|переулок|ш\.|шоссе|наб\.|"
    r"набережная|бул\.|бульвар|пл\.|площадь|мкр\.|микрорайон|тракт|проезд)"
    r"[^\n;|]{2,80}?"
    r"(?:д\.|дом|влд\.|стр\.|корп\.|к\.|литера?)\s?\d+[^\n;|]{0,40}",
    re.I,
)
_INDEX_CITY_RE = re.compile(r"\b\d{6}\b[,\s]{1,3}[А-ЯЁ][^\n;|]{5,120}")


def extract_addresses(text: str) -> list[str]:
    if not text:
        return []
    out: list[str] = []
    for rx in (_ADDR_RE, _INDEX_CITY_RE):
        for m in rx.finditer(text):
            value = re.sub(r"\s+", " ", m.group(0)).strip(" ,;.")
            if 12 <= len(value) <= 200 and value not in out:
                out.append(value)
    return out


# --- персоны ---------------------------------------------------------------

POSITIONS = (
    "генеральный директор", "исполнительный директор", "коммерческий директор",
    "финансовый директор", "технический директор", "директор по развитию",
    "директор", "president", "президент", "главный инженер", "главный бухгалтер",
    "руководитель", "учредитель", "основатель", "founder", "ceo", "cto", "cfo",
    "управляющий", "начальник", "менеджер",
)
_FIO = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?"
_FIO_SHORT = r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s?[А-ЯЁ]\."
_PERSON_RE = re.compile(
    rf"({'|'.join(POSITIONS)})\s*(?:компании|организации)?\s*[—\-–:,]?\s*({_FIO}|{_FIO_SHORT})",
    re.I,
)
_PERSON_RE_REV = re.compile(rf"({_FIO}|{_FIO_SHORT})\s*[—\-–,]\s*({'|'.join(POSITIONS)})", re.I)


def extract_persons(text: str) -> list[tuple[str, str]]:
    """Возвращает [(ФИО, должность)]."""
    if not text:
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for rx, order in ((_PERSON_RE, "pos_first"), (_PERSON_RE_REV, "fio_first")):
        for m in rx.finditer(text):
            position, fio = (m.group(1), m.group(2)) if order == "pos_first" else (m.group(2), m.group(1))
            fio = re.sub(r"\s+", " ", fio).strip()
            key = fio.lower()
            if key in seen or len(fio) < 5:
                continue
            seen.add(key)
            out.append((fio, position.lower().strip()))
    return out


# --- соцсети и мессенджеры --------------------------------------------------

SOCIAL_HOSTS = {
    "vk.com": "vk", "vkontakte.ru": "vk", "m.vk.com": "vk",
    "t.me": "telegram", "telegram.me": "telegram", "tlgg.ru": "telegram",
    "wa.me": "whatsapp", "api.whatsapp.com": "whatsapp", "chat.whatsapp.com": "whatsapp",
    "ok.ru": "odnoklassniki", "instagram.com": "instagram",
    "facebook.com": "facebook", "fb.com": "facebook",
    "linkedin.com": "linkedin", "twitter.com": "twitter", "x.com": "twitter",
    "youtube.com": "youtube", "youtu.be": "youtube", "rutube.ru": "rutube",
    "dzen.ru": "dzen", "zen.yandex.ru": "dzen", "github.com": "github",
    "habr.com": "habr", "hh.ru": "hh", "avito.ru": "avito", "yandex.ru": "yandex",
    "2gis.ru": "2gis", "flamp.ru": "flamp", "zoon.ru": "zoon",
    "tenchat.ru": "tenchat", "max.ru": "max", "viber.com": "viber",
}
_SKIP_SOCIAL_PATH = {"", "/", "/share", "/sharer", "/sharer.php", "/intent/tweet",
                     "/share.php", "/shareArticle", "/home"}


def classify_social(url: str) -> tuple[str, str] | None:
    """`https://vk.com/romashka` → ('vk', 'https://vk.com/romashka')."""
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    host = (parts.hostname or "").lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("m."):
        host = host[2:]
    network = SOCIAL_HOSTS.get(host)
    if not network:
        return None
    path = parts.path.rstrip("/")
    if path in _SKIP_SOCIAL_PATH:
        return None
    if network in ("yandex", "avito", "hh") and "/" not in path.lstrip("/"):
        return None
    clean = f"https://{host}{path}"
    return network, clean


# --- HTML ------------------------------------------------------------------

@dataclass
class PageData:
    """Всё, что вытащено с одной страницы."""
    url: str
    title: str = ""
    text: str = ""
    emails: list[str] = field(default_factory=list)
    phones: list[tuple[str, str | None, str | None]] = field(default_factory=list)
    socials: list[tuple[str, str]] = field(default_factory=list)
    requisites: dict[str, list[str]] = field(default_factory=dict)
    addresses: list[str] = field(default_factory=list)
    persons: list[tuple[str, str]] = field(default_factory=list)
    links: list[str] = field(default_factory=list)      # внутренние ссылки
    external: list[str] = field(default_factory=list)   # внешние ссылки


def html_to_text(html: str) -> str:
    if BeautifulSoup is None:  # pragma: no cover
        return re.sub(r"<[^>]+>", " ", html)
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return re.sub(r"[ \t\xa0]+", " ", soup.get_text("\n"))


def parse_page(html: str, url: str, country: str = "ru") -> PageData:
    """Разбирает страницу: контакты из текста + из ссылок mailto:/tel:."""
    page = PageData(url=url)
    if not html:
        return page
    if BeautifulSoup is None:  # pragma: no cover
        page.text = html_to_text(html)
    else:
        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.string:
            page.title = soup.title.string.strip()[:300]
        base_host = normalize_domain(url) or ""
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith("mailto:"):
                email = normalize_email(unquote(href[7:]))
                if email and email not in page.emails:
                    page.emails.append(email)
                continue
            if href.lower().startswith("tel:"):
                phone = normalize_phone(unquote(href[4:]), country)
                if phone and phone not in [p for p, _, _ in page.phones]:
                    page.phones.append((phone, None, phone_label(a.get_text(" ", strip=True))))
                continue
            if href.startswith(("javascript:", "#", "data:")):
                continue
            absolute = urljoin(url, href)
            social = classify_social(absolute)
            if social and social not in page.socials:
                page.socials.append(social)
                continue
            host = normalize_domain(absolute)
            if not host:
                continue
            if base_host and host == base_host:
                if absolute not in page.links:
                    page.links.append(absolute)
            elif absolute not in page.external:
                page.external.append(absolute)
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        page.text = re.sub(r"[ \t\xa0]+", " ", soup.get_text("\n"))

    text = page.text
    for email in extract_emails(text):
        if email not in page.emails:
            page.emails.append(email)
    # Номер из tel: уже мог попасть в список — тогда дополняем его добавочным и меткой.
    index = {p: i for i, (p, _, _) in enumerate(page.phones)}
    for phone, ext, label in extract_phones(text, country):
        if phone in index:
            i = index[phone]
            old_phone, old_ext, old_label = page.phones[i]
            page.phones[i] = (old_phone, old_ext or ext, old_label or label)
        else:
            index[phone] = len(page.phones)
            page.phones.append((phone, ext, label))
    page.requisites = extract_requisites(text)
    page.addresses = extract_addresses(text)
    page.persons = extract_persons(text)
    return page
