"""Нормализация и валидация значений: телефоны, почта, домены, ИНН/ОГРН/КПП.

Нормализация — обязательный шаг перед слиянием: «+7 (495) 123-45-67» и
«8 495 1234567» должны стать одним значением, иначе дедупликация не работает,
а уверенность не накапливается по независимым источникам.
"""
from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlsplit

# --- почта -----------------------------------------------------------------

EMAIL_RE = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63})+"
)

# Мусор, который регулярка ловит на сайтах, но почтой не является.
_EMAIL_JUNK_DOMAINS = {
    "example.com", "example.org", "domain.com", "email.com", "mail.com.ru",
    "sentry.io", "sentry-next.wixpress.com", "wixpress.com", "test.com",
    "yourdomain.com", "site.ru", "mysite.com", "company.com", "name.com",
    "godaddy.com", "w3.org", "schema.org", "googleapis.com", "gstatic.com",
}
_EMAIL_JUNK_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css",
                   ".js", ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".pdf")

# Обфускации: «ivan (собака) mail.ru», «ivan [at] mail [dot] ru».
_AT_PATTERNS = [
    (re.compile(r"\s*[\(\[\{]\s*(?:at|собака|сбк|аt)\s*[\)\]\}]\s*", re.I), "@"),
    (re.compile(r"\s+(?:at|собака)\s+", re.I), "@"),
    (re.compile(r"\s*&#64;\s*"), "@"),
    (re.compile(r"\s*&#0?64;\s*"), "@"),
]
_DOT_PATTERNS = [
    (re.compile(r"\s*[\(\[\{]\s*(?:dot|точка|тчк)\s*[\)\]\}]\s*", re.I), "."),
    (re.compile(r"\s+(?:dot|точка)\s+", re.I), "."),
]

ROLE_LOCALPARTS = {
    "info", "mail", "office", "sales", "support", "help", "contact", "contacts",
    "admin", "hello", "hr", "job", "jobs", "zakaz", "order", "orders", "shop",
    "market", "reception", "secretary", "buh", "buhgalteria", "post", "pochta",
    "client", "clients", "manager", "team", "press", "pr", "noreply",
    "no-reply", "webmaster", "postmaster", "abuse", "director", "dir",
}


def deobfuscate(text: str) -> str:
    """Разворачивает «человеческие» способы спрятать почту от парсеров."""
    out = text
    for rx, repl in _AT_PATTERNS + _DOT_PATTERNS:
        out = rx.sub(repl, out)
    return out


def normalize_email(raw: str) -> str | None:
    if not raw:
        return None
    value = unicodedata.normalize("NFKC", raw).strip()
    value = value.replace("mailto:", "").split("?")[0].strip()
    if "@" not in value:
        # «ivan (собака) mail.ru» — обфускация от наивных парсеров
        value = deobfuscate(value)
    value = value.strip().strip(".,;:<>()[]\"'«»").lower()
    if value.count("@") != 1:
        return None
    local, _, domain = value.partition("@")
    if not local or not domain or ".." in value or value.startswith("."):
        return None
    if local.endswith(".") or domain.startswith("-") or domain.endswith("-"):
        return None
    if any(value.endswith(ext) for ext in _EMAIL_JUNK_EXT):
        return None
    if domain in _EMAIL_JUNK_DOMAINS:
        return None
    tld = domain.rsplit(".", 1)[-1]
    if len(tld) < 2 or tld.isdigit():
        return None
    if not EMAIL_RE.fullmatch(value):
        return None
    return value


def is_role_email(email: str) -> bool:
    """Общая почта отдела (info@, sales@) — не привязана к человеку."""
    local = email.split("@", 1)[0]
    return local.split("+")[0] in ROLE_LOCALPARTS


def email_domain(email: str) -> str:
    return email.split("@", 1)[1] if "@" in email else ""


# --- телефоны --------------------------------------------------------------

_EXT_RE = re.compile(r"(?:доб|вн|ext|extension)\.?\s*[:№#]?\s*(\d{1,6})", re.I)
_PHONE_CANDIDATE_RE = re.compile(
    r"(?:\+7|\+?[1-9]\d{0,2})?[\s\-().]{0,3}"
    r"(?:\(?\d{2,5}\)?[\s\-().]{0,3}){1,4}\d{2,4}"
)


def normalize_phone(raw: str, default_country: str = "ru") -> str | None:
    """Приводит номер к E.164 (`+74951234567`). Внутренний добавочный отбрасывается.

    Возвращает None, если из строки не получается правдоподобный номер.
    """
    if not raw:
        return None
    text = unicodedata.normalize("NFKC", str(raw))
    text = _EXT_RE.sub("", text)
    plus = "+" in text
    digits = re.sub(r"\D", "", text)
    if not digits:
        return None
    if default_country == "ru":
        # 8 (495) ... → 7495...; 495 ... (10 цифр) → 7495...
        if len(digits) == 11 and digits[0] == "8":
            digits = "7" + digits[1:]
        elif len(digits) == 10 and not plus:
            digits = "7" + digits
    if len(digits) < 8 or len(digits) > 15:
        return None
    if digits[0] == "0":
        return None
    # Отсекаем «номера» из повторяющихся цифр и дат.
    if len(set(digits)) <= 2:
        return None
    return "+" + digits


def phone_extension(raw: str) -> str | None:
    m = _EXT_RE.search(raw or "")
    return m.group(1) if m else None


def format_phone_ru(e164: str) -> str:
    """Человекочитаемый вид для отчёта: +7 (495) 123-45-67."""
    d = e164.lstrip("+")
    if len(d) == 11 and d.startswith("7"):
        return f"+7 ({d[1:4]}) {d[4:7]}-{d[7:9]}-{d[9:11]}"
    return e164


# --- домены и ссылки -------------------------------------------------------

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def normalize_domain(raw: str) -> str | None:
    """`https://WWW.Example.RU/contacts?x=1` → `example.ru`."""
    if not raw:
        return None
    value = raw.strip().lower()
    if "://" not in value:
        value = "//" + value
    host = urlsplit(value).hostname or ""
    host = host.rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return None
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if not _DOMAIN_RE.match(host):
        return None
    return host


def registrable_domain(host: str) -> str:
    """Грубое определение домена 2-го уровня с учётом частых составных зон."""
    parts = (host or "").split(".")
    if len(parts) <= 2:
        return host
    two = ".".join(parts[-2:])
    compound = {"com.ru", "net.ru", "org.ru", "co.uk", "com.ua", "co.il",
                "com.tr", "com.br", "com.cn", "co.jp", "org.uk", "gov.uk"}
    if two in compound and len(parts) >= 3:
        return ".".join(parts[-3:])
    return two


def same_site(a: str, b: str) -> bool:
    da, db = normalize_domain(a), normalize_domain(b)
    if not da or not db:
        return False
    return registrable_domain(da) == registrable_domain(db)


# --- российские реквизиты --------------------------------------------------

def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def validate_inn(raw: str) -> bool:
    """Контрольная сумма ИНН: 10 знаков (юрлицо) или 12 (ИП/физлицо)."""
    inn = _digits(raw)
    if len(inn) == 10:
        coef = (2, 4, 10, 3, 5, 9, 4, 6, 8)
        checksum = sum(int(d) * c for d, c in zip(inn[:9], coef)) % 11 % 10
        return checksum == int(inn[9])
    if len(inn) == 12:
        c1 = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        c2 = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
        n11 = sum(int(d) * c for d, c in zip(inn[:10], c1)) % 11 % 10
        n12 = sum(int(d) * c for d, c in zip(inn[:11], c2)) % 11 % 10
        return n11 == int(inn[10]) and n12 == int(inn[11])
    return False


def validate_ogrn(raw: str) -> bool:
    """Контрольная цифра ОГРН (13 знаков) или ОГРНИП (15 знаков)."""
    ogrn = _digits(raw)
    if len(ogrn) == 13:
        return int(ogrn[:12]) % 11 % 10 == int(ogrn[12])
    if len(ogrn) == 15:
        return int(ogrn[:14]) % 13 % 10 == int(ogrn[14])
    return False


def validate_kpp(raw: str) -> bool:
    value = (raw or "").strip().upper()
    return bool(re.fullmatch(r"\d{4}[\dA-Z]{2}\d{3}", value))


def normalize_inn(raw: str) -> str | None:
    inn = _digits(raw)
    return inn if validate_inn(inn) else None


def normalize_ogrn(raw: str) -> str | None:
    ogrn = _digits(raw)
    return ogrn if validate_ogrn(ogrn) else None


def entity_kind_by_inn(inn: str) -> str | None:
    """10 знаков — организация, 12 — ИП/физлицо."""
    inn = _digits(inn)
    if len(inn) == 10:
        return "organization"
    if len(inn) == 12:
        return "individual"
    return None


# --- наименования ----------------------------------------------------------

_LEGAL_FORMS = (
    "ооо", "оао", "зао", "пао", "ао", "ип", "нко", "ано", "тсж", "гуп", "муп",
    "фгуп", "оаэ", "llc", "ltd", "inc", "gmbh", "corp", "co", "plc", "sa", "bv",
)


def normalize_company_name(raw: str) -> str | None:
    """Схлопывает кавычки/пробелы, но сохраняет исходный регистр слов."""
    if not raw:
        return None
    value = unicodedata.normalize("NFKC", raw)
    value = value.replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip(" \t\n\r.,;")
    return value or None


def name_key(raw: str) -> str:
    """Ключ сравнения наименований: без формы собственности, кавычек и регистра."""
    value = (normalize_company_name(raw) or "").lower()
    value = re.sub(r"[\"'`]", " ", value)
    tokens = [t for t in re.split(r"[\s,.]+", value) if t]
    tokens = [t for t in tokens if t not in _LEGAL_FORMS]
    return " ".join(tokens).strip()


# --- транслитерация --------------------------------------------------------

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def translit_ru(text: str) -> str:
    """Кириллица → латиница по правилам загранпаспорта (для почтовых логинов)."""
    out: list[str] = []
    for ch in (text or "").lower():
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum() or ch in "-_.":
            out.append(ch)
    return "".join(out)
