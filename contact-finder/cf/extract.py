"""Извлечение контактов из произвольного HTML/текста.

Принцип: никаких CSS-селекторов. Селекторы ломаются при каждом редизайне
сайта-агрегатора. Вместо этого — нормализация текста и поиск по шаблонам,
плюс обязательная проверка, что на странице присутствует нужный ИНН.
"""
from __future__ import annotations

import html as html_mod
import re

# ---------------------------------------------------------------- HTML → текст

_SCRIPT_STYLE = re.compile(
    r"<(script|style|noscript|template)\b[^>]*>.*?</\1>", re.I | re.S
)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t   ]+")


def strip_html(raw: str) -> str:
    """HTML → плоский текст, пригодный для регулярок."""
    text = _SCRIPT_STYLE.sub(" ", raw)
    text = _TAG.sub(" ", text)
    text = html_mod.unescape(text)
    text = text.replace("­", "")  # мягкий перенос
    text = _WS.sub(" ", text)
    return text


# ---------------------------------------------------------------- телефоны

# Кандидат: 10-25 символов из цифр и типичных разделителей.
_PHONE_CANDIDATE = re.compile(r"(?<![\d])[\+\d][\d\s\-\(\)\.]{8,24}\d(?![\d])")
_TEL_HREF = re.compile(r"""href\s*=\s*["']tel:([^"']+)["']""", re.I)

# Номера, которые почти всегда являются мусором, а не контактом компании.
_JUNK_PREFIXES = (
    "70000000",  # заглушки
    "78000000",
)


def normalize_phone(raw: str) -> str | None:
    """Приводит номер к виду +7XXXXXXXXXX. Возвращает None, если это не телефон."""
    digits = re.sub(r"\D", "", raw or "")

    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    elif len(digits) == 10:
        # Городской/мобильный без кода страны.
        digits = "7" + digits
    else:
        return None

    if digits[1] == "0":  # кода 0XX в России не существует
        return None
    if digits.startswith(_JUNK_PREFIXES):
        return None
    if len(set(digits[1:])) <= 2:  # 79999999999 и подобные заглушки
        return None

    return "+" + digits


def format_phone(normalized: str) -> str:
    """+79312389581 → +7 (931) 238-95-81"""
    d = normalized.lstrip("+")
    if len(d) != 11:
        return normalized
    return f"+{d[0]} ({d[1:4]}) {d[4:7]}-{d[7:9]}-{d[9:11]}"


def phones_from_html(raw_html: str) -> list[str]:
    """Телефоны из tel:-ссылок. Самый точный источник — их и берём первыми."""
    out: list[str] = []
    for match in _TEL_HREF.findall(raw_html or ""):
        phone = normalize_phone(html_mod.unescape(match))
        if phone and phone not in out:
            out.append(phone)
    return out


# Маркеры реквизитов: если стоят прямо перед числом — это не телефон.
_REQUISITE_CONTEXT = re.compile(
    r"(инн|кпп|огрн(?:ип)?|окпо|окато|октмо|бик|уин|р/?с|к/?с|"
    r"сч[её]т|account|карт[аы])[^\w]{0,4}$",
    re.I,
)


def phones_from_text(text: str) -> list[str]:
    """Телефоны из плоского текста.

    Кандидат принимается, только если он выглядит как телефон, а не как
    кусок ОГРН/ИНН/счёта: требуется префикс +7/8 или разделители, и рядом
    не должно стоять слово-маркер реквизита (ИНН, ОГРН, БИК, счёт…).
    """
    out: list[str] = []
    for match in _PHONE_CANDIDATE.finditer(text or ""):
        chunk = match.group(0)
        digits = re.sub(r"\D", "", chunk)

        has_separator = bool(re.search(r"[\-\(\)\.]", chunk))  # без пробела!
        has_country_code = chunk.lstrip().startswith(("+7", "8"))
        if not has_separator and not has_country_code:
            continue
        # Сплошная строка из 12+ цифр — это ОГРН/ИНН/счёт, а не телефон.
        if not has_separator and len(digits) > 11:
            continue
        # Число сразу после «ИНН»/«ОГРН»/«БИК»/«счёт» — реквизит, не телефон.
        prefix = text[max(0, match.start() - 12): match.start()]
        if _REQUISITE_CONTEXT.search(prefix):
            continue

        phone = normalize_phone(chunk)
        if phone and phone not in out:
            out.append(phone)
    return out


def extract_phones(raw_html: str) -> list[str]:
    """Все телефоны страницы: сначала из tel:, затем из текста."""
    out = phones_from_html(raw_html)
    for phone in phones_from_text(strip_html(raw_html)):
        if phone not in out:
            out.append(phone)
    return out


# ---------------------------------------------------------------- почта и сайт

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_EMAIL_JUNK_DOMAINS = (
    "example.com", "sentry.io", "domain.com", "mail.ru.ru", "yandex.ru.ru",
)
_EMAIL_JUNK_LOCAL = ("noreply", "no-reply", "support@rusprofile", "info@checko")


def extract_emails(raw_html: str) -> list[str]:
    text = strip_html(raw_html)
    out: list[str] = []
    for candidate in _EMAIL.findall(text):
        low = candidate.lower()
        if low.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            continue
        if any(dom in low for dom in _EMAIL_JUNK_DOMAINS):
            continue
        if any(bad in low for bad in _EMAIL_JUNK_LOCAL):
            continue
        if low not in out:
            out.append(low)
    return out


# Домены агрегаторов — это не сайт искомой компании.
AGGREGATOR_DOMAINS = {
    "rusprofile.ru", "checko.ru", "list-org.com", "sbis.ru", "saby.ru",
    "zachestnyibiznes.ru", "spark-interfax.ru", "audit-it.ru", "tbank.ru",
    "focus.kontur.ru", "companies.rbc.ru", "rbc.ru", "datanewton.ru",
    "synapsenet.ru", "vypiska-nalog.com", "e-ecolog.ru", "nalog.ru",
    "nalog.gov.ru", "zakupki.gov.ru", "google.com", "yandex.ru", "2gis.ru",
    "vk.com", "vk.ru", "facebook.com", "instagram.com", "youtube.com",
    "t.me", "wa.me", "companium.ru", "casebook.ru", "b2b-center.ru",
    "check.tochka.com", "klerk.ru", "moedelo.org", "vbr.ru", "ogrn.su",
    "injust.pro", "testfirm.ru", "conventions.ru", "orgs.biz", "yp.ru",
    "zoon.ru", "spravker.ru", "orgpage.ru", "vbankcenter.ru", "upfox.ru",
}


def is_aggregator(url_or_domain: str) -> bool:
    low = (url_or_domain or "").lower()
    return any(dom in low for dom in AGGREGATOR_DOMAINS)


# ---------------------------------------------------------------- проверка ИНН

_DIGITS_ONLY = re.compile(r"\D")


def page_mentions_inn(raw_html: str, inn: str) -> bool:
    """Есть ли на странице искомый ИНН.

    Сравниваем по «цифровому следу» страницы, чтобы пережить любую
    разметку: «ИНН 7838 499 969», «7838499969</span>» и т.п.
    """
    if not inn:
        return False
    text = strip_html(raw_html)
    if inn in text:
        return True
    # Запасной путь: убираем всё, кроме цифр, и ищем подстроку.
    return inn in _DIGITS_ONLY.sub("", text)


def inn_checksum_valid(inn: str) -> bool:
    """Проверка контрольных цифр ИНН (10 знаков — ЮЛ, 12 — ИП/физлицо)."""
    if not inn or not inn.isdigit():
        return False

    def check(digits: str, weights: list[int]) -> int:
        return sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10

    if len(inn) == 10:
        return check(inn[:9], [2, 4, 10, 3, 5, 9, 4, 6, 8]) == int(inn[9])
    if len(inn) == 12:
        first = check(inn[:10], [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
        second = check(inn[:11], [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
        return first == int(inn[10]) and second == int(inn[11])
    return False


# ---------------------------------------------------------------- КПП и ОГРН

_OGRN = re.compile(r"(?<!\d)(\d{13}|\d{15})(?!\d)")
_KPP_LABELED = re.compile(r"КПП[^\d]{0,15}(\d{9})")


def guess_kpp(raw_html: str, inn: str) -> str | None:
    """КПП со страницы; если не нашли — типовой для ЮЛ (первые 4 цифры ИНН + 01001)."""
    match = _KPP_LABELED.search(strip_html(raw_html))
    if match:
        return match.group(1)
    if len(inn) == 10:
        return inn[:4] + "01001"
    return None


def default_kpp(inn: str) -> str | None:
    return inn[:4] + "01001" if len(inn) == 10 else None


def find_ogrn(raw_html: str) -> str | None:
    match = _OGRN.search(strip_html(raw_html))
    return match.group(1) if match else None
