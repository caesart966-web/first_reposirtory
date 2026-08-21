"""
Низкоуровневые утилиты нормализации текста и распознавания значений.

Здесь собрано всё, что не зависит ни от Excel, ни от HTTP:

* приведение произвольной ячейки Excel к строке;
* нормализация заголовков колонок (для сопоставления «любых» названий);
* проверка ИНН по контрольной сумме и поиск ИНН в свободном тексте;
* разбор дат в любых встречающихся форматах (включая серийные числа Excel);
* извлечение и нормализация телефонов, email, адресов, ФИО руководителя.
"""

from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------- #
#                        Приведение ячейки к строке                            #
# --------------------------------------------------------------------------- #

#: Значения, которые считаем «пустыми» независимо от регистра.
_EMPTY_TOKENS: frozenset[str] = frozenset(
    {
        "", "-", "--", "---", "—", "–", "нет", "н/д", "нд", "n/a", "na", "none",
        "null", "nan", "nat", "не указан", "не указано", "не указана", "отсутствует",
        "нет данных", "без данных", "#н/д", "#n/a", "0",
    }
)


def is_blank(value: Any) -> bool:
    """True, если значение пустое или является «заглушкой» вида «—», «н/д», NaN."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    text = str(value).strip().lower().replace("ё", "е")
    return text in _EMPTY_TOKENS


def cell_to_text(value: Any) -> str:
    """
    Аккуратно превращает значение ячейки Excel в строку.

    Особые случаи:
    * ``7707083893.0`` (float без дробной части) -> ``"7707083893"``
      — иначе ИНН, прочитанный как число, потеряет вид;
    * ``datetime``/``date``  -> ``"ДД.ММ.ГГГГ"``;
    * ``None``/``NaN``       -> ``""``.
    """
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return ""
        if value.is_integer():
            return str(int(value))
        return repr(value).rstrip("0").rstrip(".")
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y") if (value.hour, value.minute, value.second) == (0, 0, 0) \
            else value.strftime("%d.%m.%Y %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, bytes):
        for encoding in ("utf-8", "cp1251", "cp866"):
            try:
                return value.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace").strip()
    text = str(value)
    # Excel любит подставлять неразрывные пробелы и «мягкие переносы».
    text = text.replace("\xa0", " ").replace("​", "").replace("­", "")
    return " ".join(text.split()).strip()


def clean_text(value: Any) -> str:
    """То же, что :func:`cell_to_text`, но «заглушки» превращаются в пустую строку."""
    text = cell_to_text(value)
    return "" if is_blank(text) else text


# --------------------------------------------------------------------------- #
#                        Нормализация заголовков колонок                       #
# --------------------------------------------------------------------------- #

_NON_WORD_RE = re.compile(r"[^0-9a-zа-я]+")


def normalize_header(value: Any) -> str:
    """
    Приводит заголовок колонки к канонической форме для сравнения с шаблонами.

    ``"  Полное  наименование\\nчлена СРО (ЮЛ/ИП) "`` -> ``"полное наименование члена сро юл ип"``.
    Регистр, «ё», пунктуация, переносы строк и лишние пробелы игнорируются,
    поэтому шаблоны в :mod:`nostroy_checko.column_mapper` не зависят от оформления.
    """
    text = cell_to_text(value).lower().replace("ё", "е")
    text = unicodedata.normalize("NFKC", text)
    text = _NON_WORD_RE.sub(" ", text)
    return " ".join(text.split())


def normalize_company_name(value: Any) -> str:
    """
    Каноническая форма названия компании — используется как ключ дедупликации,
    когда ИНН отсутствует. Убираются кавычки любых видов, регистр и лишние пробелы.
    Организационно-правовая форма НЕ отбрасывается: «ООО Ромашка» и «АО Ромашка» —
    разные юрлица.
    """
    text = cell_to_text(value).upper().replace("Ё", "Е")
    text = re.sub(r'[«»"“”„`\']', " ", text)
    text = re.sub(r"[^0-9A-ZА-Я]+", " ", text)
    return " ".join(text.split())


# --------------------------------------------------------------------------- #
#                                    ИНН                                       #
# --------------------------------------------------------------------------- #

_INN_10_WEIGHTS: tuple[int, ...] = (2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN_12_WEIGHTS_11: tuple[int, ...] = (7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
_INN_12_WEIGHTS_12: tuple[int, ...] = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)

#: Числовые последовательности длиной 10 или 12, не входящие в более длинные.
_INN_TOKEN_RE = re.compile(r"(?<!\d)(\d{10}|\d{12})(?!\d)")


def _inn_checksum_digit(digits: Sequence[int], weights: Sequence[int]) -> int:
    """Контрольная цифра ИНН по заданным весовым коэффициентам ФНС."""
    return sum(d * w for d, w in zip(digits, weights)) % 11 % 10


def is_valid_inn(value: Any) -> bool:
    """
    Проверяет ИНН по официальному алгоритму контрольных сумм ФНС.

    Поддерживаются оба варианта: 10 знаков (юрлицо) и 12 знаков (ИП/физлицо).
    """
    text = re.sub(r"\D", "", cell_to_text(value))
    if len(text) not in (10, 12) or not text.isdigit():
        return False
    digits = [int(ch) for ch in text]
    if len(digits) == 10:
        return digits[9] == _inn_checksum_digit(digits[:9], _INN_10_WEIGHTS)
    return (
        digits[10] == _inn_checksum_digit(digits[:10], _INN_12_WEIGHTS_11)
        and digits[11] == _inn_checksum_digit(digits[:11], _INN_12_WEIGHTS_12)
    )


def normalize_inn(value: Any) -> str:
    """
    Возвращает ИНН из значения ячейки в виде строки из 10/12 цифр либо "".

    Обрабатывает частые артефакты выгрузок: ``"ИНН 7707083893"``,
    ``"7707083893 / 770701001"`` (ИНН/КПП), ``7707083893.0``, ``"77 07 08 38 93"``.
    Ведущие нули не теряются, потому что работаем со строками.
    """
    text = cell_to_text(value)
    if not text:
        return ""
    # 1) Явный ИНН в тексте (с валидной контрольной суммой) — самый надёжный вариант.
    for candidate in _INN_TOKEN_RE.findall(text):
        if is_valid_inn(candidate):
            return candidate
    # 2) Ячейка состоит только из цифр и разделителей — склеиваем и проверяем длину.
    compact = re.sub(r"[\s\-]", "", text)
    if re.fullmatch(r"\d{10}|\d{12}", compact):
        return compact
    # 3) ИНН/КПП одной строкой: берём часть до разделителя.
    head = re.split(r"[/\\|,;]", text, maxsplit=1)[0]
    head_digits = re.sub(r"\D", "", head)
    if len(head_digits) in (10, 12):
        return head_digits
    # 4) Последняя попытка: первая последовательность нужной длины без проверки суммы.
    match = _INN_TOKEN_RE.search(text)
    return match.group(1) if match else ""


def find_inns_in_row(values: Iterable[Any]) -> list[str]:
    """
    Ищет все валидные ИНН в произвольной строке таблицы.

    Нужна, когда колонка с ИНН не опознана по заголовку: ни одна запись
    не должна потеряться только из-за нестандартной шапки.
    """
    found: list[str] = []
    for value in values:
        text = cell_to_text(value)
        if not text:
            continue
        for candidate in _INN_TOKEN_RE.findall(text):
            if is_valid_inn(candidate) and candidate not in found:
                found.append(candidate)
    return found


_OGRN_TOKEN_RE = re.compile(r"(?<!\d)(\d{13}|\d{15})(?!\d)")


def normalize_ogrn(value: Any) -> str:
    """Возвращает ОГРН/ОГРНИП (13 или 15 цифр) из значения ячейки либо ""."""
    text = cell_to_text(value)
    match = _OGRN_TOKEN_RE.search(re.sub(r"[\s\-]", "", text))
    return match.group(1) if match else ""


# --------------------------------------------------------------------------- #
#                                    Даты                                      #
# --------------------------------------------------------------------------- #

_RU_MONTHS: dict[str, int] = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4, "мая": 5, "май": 5,
    "июн": 6, "июл": 7, "август": 8, "сентябр": 9, "октябр": 10,
    "ноябр": 11, "декабр": 12,
}

_DATE_FORMATS: tuple[str, ...] = (
    "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y",
    "%Y.%m.%d", "%Y/%m/%d", "%d %m %Y", "%m/%d/%Y", "%Y%m%d",
    "%d.%m.%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y г.", "%d.%m.%Yг.",
)

#: Строка «похожа на дату», если содержит два разделителя или название месяца.
_DATE_LIKE_RE = re.compile(
    r"(\d{1,4}[.\-/\s]\d{1,2}[.\-/\s]\d{2,4})|(\d{1,2}\s+[а-яё]{3,10}\s+\d{4})",
    re.IGNORECASE,
)

_RU_DATE_RE = re.compile(r"(\d{1,2})\s+([а-яё]{3,10})\.?\s+(\d{4})", re.IGNORECASE)

#: Границы разумных дат реестра — защищают от мусора вроде «01.01.1900».
_MIN_DATE = date(1950, 1, 1)
_MAX_DATE = date(2100, 12, 31)


def excel_serial_to_date(serial: float, date_mode: int = 0) -> date | None:
    """
    Переводит «серийное» число Excel в дату.

    :param serial:    число дней от эпохи Excel;
    :param date_mode: 0 — система 1900 (Windows), 1 — система 1904 (старый Mac).
    """
    try:
        serial = float(serial)
    except (TypeError, ValueError):
        return None
    if serial <= 0 or serial > 2958465:      # 2958465 == 31.12.9999
        return None
    epoch = date(1899, 12, 30) if date_mode == 0 else date(1904, 1, 1)
    try:
        result = epoch + timedelta(days=int(serial))
    except (OverflowError, ValueError):
        return None
    return result


def parse_date(value: Any, date_mode: int = 0) -> date | None:
    """
    Разбирает дату из значения ячейки любого типа.

    Поддерживаются:
    * готовые ``datetime``/``date`` из openpyxl;
    * серийные числа Excel (``40123`` -> 22.11.2009);
    * «голый» год (``2010`` -> 01.01.2010) — встречается в колонках «Год вступления»;
    * строки во всех распространённых форматах, включая «12 мая 2010 г.».

    Возвращает ``None``, если распознать дату не удалось (мы никогда не «угадываем»).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, bool):
        return None

    # --- числовые значения -------------------------------------------------- #
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        number = float(value)
        # «Голый» год: в реестрах бывает колонка «Год вступления».
        if float(number).is_integer() and 1900 <= number <= 2100:
            return date(int(number), 1, 1)
        result = excel_serial_to_date(number, date_mode)
        return result if result and _MIN_DATE <= result <= _MAX_DATE else None

    text = clean_text(value)
    if not text:
        return None

    # Строка-число («40123» или «2010») — та же логика, что и выше.
    if re.fullmatch(r"\d{1,5}(?:[.,]0+)?", text):
        return parse_date(float(text.replace(",", ".")), date_mode)

    if not _DATE_LIKE_RE.search(text):
        return None

    # --- русские названия месяцев ------------------------------------------ #
    ru_match = _RU_DATE_RE.search(text)
    if ru_match:
        day, month_word, year = ru_match.groups()
        month_word = month_word.lower().replace("ё", "е")
        for stem, month in _RU_MONTHS.items():
            if month_word.startswith(stem):
                try:
                    result = date(int(year), month, int(day))
                except ValueError:
                    break
                return result if _MIN_DATE <= result <= _MAX_DATE else None

    # --- строгие форматы ---------------------------------------------------- #
    compact = text.replace(" ", " ").strip()
    for fmt in _DATE_FORMATS:
        try:
            result = datetime.strptime(compact, fmt).date()
        except ValueError:
            continue
        if _MIN_DATE <= result <= _MAX_DATE:
            return result

    # --- «первая дата внутри строки» --------------------------------------- #
    inner = _DATE_LIKE_RE.search(compact)
    if inner and inner.group(0) != compact:
        return parse_date(inner.group(0), date_mode)

    # --- запасной разбор через dateutil (день впереди месяца) --------------- #
    # Режим fuzzy НЕ используется намеренно: он «додумывает» дату из любого
    # текста — фраза «в июле 2021 года ошибочно...» превращалась в конкретное
    # число, и в отчёт попадала выдуманная дата. Лучше не вернуть ничего,
    # чем вернуть неверное.
    if len(compact) > 32:
        return None
    try:
        from dateutil import parser as dateutil_parser  # необязательная зависимость
    except ImportError:
        return None
    try:
        result = dateutil_parser.parse(compact, dayfirst=True).date()
    except (ValueError, OverflowError, TypeError):
        return None
    return result if _MIN_DATE <= result <= _MAX_DATE else None


def is_date_cell(value: Any, date_mode: int = 0) -> bool:
    """
    Похожа ли ячейка на поле с датой (а не на текст, где дата упомянута).

    Используется при автоопределении роли столбца. Разница принципиальная:
    в ячейке «Протокол № 15 от 12.05.2010» дата — это содержимое поля, а в
    примечании «дата рождения 03.05.1970, место рождения -пос. Ропша...» —
    просто упоминание. Без этой проверки колонка примечаний становилась
    «датой исключения».
    """
    if isinstance(value, (date, datetime)):
        return True
    text = clean_text(value)
    if not text or parse_date(value, date_mode) is None:
        return False
    match = _DATE_LIKE_RE.search(text)
    if match is None:
        return len(text) <= 12          # серийное число или «голый» год
    # Вокруг даты допускается короткая подпись («от», «Протокол № 15»),
    # но не предложение из нескольких слов.
    remainder = (text[: match.start()] + text[match.end() :])
    letters = sum(1 for char in remainder if char.isalpha())
    return letters <= 16


def format_date(value: date | None) -> str:
    """Дата в человекочитаемом виде ``ДД.ММ.ГГГГ`` (пустая строка для ``None``)."""
    return value.strftime("%d.%m.%Y") if value else ""


# --------------------------------------------------------------------------- #
#                          Телефоны / email / сайты                            #
# --------------------------------------------------------------------------- #

#: Кандидат в телефон: начинается и заканчивается цифрой, внутри — цифры и разделители.
_PHONE_CANDIDATE_RE = re.compile(r"\+?\d[\d\-\s().]{6,24}\d")

_EMAIL_RE = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")

_URL_RE = re.compile(
    r"(?:https?://|www\.)[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+", re.IGNORECASE
)


def normalize_phone(value: Any) -> str:
    """
    Приводит телефон к виду ``+7XXXXXXXXXX``.

    Если номер не российский или не удалось распознать длину — возвращается
    исходная строка без лишних пробелов (данные не теряем никогда).
    """
    text = cell_to_text(value)
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if not digits:
        return ""
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    if text.startswith("+") and 8 <= len(digits) <= 15:
        return "+" + digits
    return " ".join(text.split())


def _looks_like_phone(raw: str) -> bool:
    """
    Отсеивает ложные срабатывания: ИНН, ОГРН, даты, номера свидетельств.

    «Голая» последовательность из 10 цифр без разделителей и без префикса 8/+7
    в реестре почти всегда ИНН, а не телефон.
    """
    digits = re.sub(r"\D", "", raw)
    if len(digits) not in (10, 11):
        return False
    if len(set(digits)) <= 2:                      # 0000000000, 1111111111
        return False
    if len(digits) == 11 and digits[0] not in "78":
        return False
    has_separator = bool(re.search(r"[\s\-().]", raw.strip()))
    has_prefix = raw.strip().startswith("+") or (len(digits) == 11 and digits[0] in "78")
    if len(digits) == 10 and not has_separator and not has_prefix:
        return False                               # скорее всего ИНН
    if len(digits) == 10 and not has_prefix and is_valid_inn(digits):
        return False                               # контрольная сумма ИНН сходится
    return True


def extract_phones(value: Any, limit: int = 20) -> list[str]:
    """
    Достаёт из произвольного текста все телефоны в нормализованном виде.

    Работает и с ячейкой ``"8(495)123-45-67, +7 916 000-00-00 доб.5"``,
    и со свободным текстом страницы checko.ru.
    """
    text = cell_to_text(value)
    if not text:
        return []
    results: list[str] = []
    for match in _PHONE_CANDIDATE_RE.finditer(text):
        raw = match.group(0)
        if not _looks_like_phone(raw):
            continue
        phone = normalize_phone(raw)
        if phone and phone not in results:
            results.append(phone)
            if len(results) >= limit:
                break
    return results


def extract_emails(value: Any, limit: int = 20) -> list[str]:
    """Достаёт из текста все email-адреса (в нижнем регистре, без дублей)."""
    text = cell_to_text(value)
    if not text:
        return []
    # Частый артефакт выгрузок: «ivanov @ mail.ru» или «ivanov(собака)mail.ru».
    text = re.sub(r"\s*@\s*", "@", text)
    text = re.sub(r"\s*\((?:собака|at|а)\)\s*", "@", text, flags=re.IGNORECASE)
    results: list[str] = []
    for match in _EMAIL_RE.finditer(text):
        email = match.group(0).lower().strip(" .,;")
        # Отбрасываем «хвост» вида mail.ru.Тел (склейка колонок).
        email = re.sub(r"\.+$", "", email)
        if email and email not in results and "." in email.split("@")[-1]:
            results.append(email)
            if len(results) >= limit:
                break
    return results


def extract_urls(value: Any, limit: int = 10) -> list[str]:
    """Достаёт из текста адреса сайтов."""
    text = cell_to_text(value)
    if not text:
        return []
    results: list[str] = []
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;)")
        if url not in results:
            results.append(url)
            if len(results) >= limit:
                break
    return results


# --------------------------------------------------------------------------- #
#                       Признаки названий, адресов и ФИО                       #
# --------------------------------------------------------------------------- #

#: Организационно-правовые формы и маркеры названия юрлица/ИП.
_ORG_MARKERS: tuple[str, ...] = (
    "ооо", "оао", "зао", "пао", "ао", "нао", "ип", "гуп", "муп", "фгуп", "мбу", "гбу",
    "фгбу", "нко", "ано", "тсж", "ск", "общество с ограниченной ответственностью",
    "акционерное общество", "публичное акционерное", "закрытое акционерное",
    "открытое акционерное", "индивидуальный предприниматель", "унитарное предприятие",
    "производственный кооператив", "крестьянское", "товарищество", "учреждение",
    "предприятие", "корпорация", "холдинг", "концерн", "фирма", "компания", "трест",
)

#: Слова-маркеры адреса.
_ADDRESS_MARKERS: tuple[str, ...] = (
    "обл", "область", "край", "респ", "республика", "г.", "гор.", "город", "р-н",
    "район", "ул.", "улица", "пр-т", "проспект", "просп", "пер.", "переулок", "д.",
    "дом", "корп", "стр.", "строение", "кв.", "офис", "оф.", "помещ", "шоссе", "ш.",
    "наб.", "набережная", "мкр", "микрорайон", "б-р", "бульвар", "пл.", "площадь",
    "тер.", "территория", "владение", "влд", "литер", "этаж", "рп ", "пгт", "снт",
)

_POSTAL_INDEX_RE = re.compile(r"(?<!\d)\d{6}(?!\d)")

#: ФИО из трёх слов с заглавных букв (Иванов Иван Иванович) или «Иванов И.И.».
_FIO_RE = re.compile(
    r"[А-ЯЁ][а-яё\-]{1,30}\s+(?:[А-ЯЁ][а-яё\-]{1,30}\s+[А-ЯЁ][а-яё\-]{1,30}"
    r"|[А-ЯЁ]\.\s?[А-ЯЁ]\.)"
)


def has_org_marker(value: Any) -> bool:
    """
    Есть ли в значении явная организационно-правовая форма или кавычки названия.

    Самый сильный признак колонки с наименованием: «ООО ...», «АО ...»,
    «ИП Иванов И.И.», «... «Ромашка»».
    """
    text = clean_text(value)
    if not text:
        return False
    lowered = text.lower().replace("ё", "е")
    if re.search(r'[«»"“”]', text):
        return True
    return any(
        re.search(rf"(?<![а-я]){re.escape(marker)}(?![а-я])", lowered)
        for marker in _ORG_MARKERS
    )


def looks_like_company_name(value: Any) -> bool:
    """Похоже ли значение на наименование организации/ИП."""
    text = clean_text(value)
    if len(text) < 3:
        return False
    lowered = text.lower().replace("ё", "е")
    if any(re.search(rf"(?<![а-я]){re.escape(marker)}", lowered) for marker in _ORG_MARKERS):
        return True
    if re.search(r'[«"“]', text):                   # кавычки в названии
        return True
    letters = sum(ch.isalpha() for ch in text)
    return letters >= 6 and letters / max(len(text), 1) > 0.5


# Внутригородская территория в формате ФИАС. «Муниципальный округ» —
# административная единица, для контактного адреса бесполезная: она добавляет
# к строке до 50 символов, ячейка переносится на три строки и один адрес
# читается как несколько. «Город» внутри города (Кронштадт, Петергоф) —
# наоборот, часть адреса, его сохраняем в привычной записи.
_INNER_OKRUG_RE = re.compile(
    r",?\s*вн\.\s*тер\.\s*г\.\s*муниципальн\w*\s+округ\s+[^,]+", re.IGNORECASE
)
_INNER_CITY_RE = re.compile(
    r",?\s*вн\.\s*тер\.\s*г\.\s*(?:город|г\.)\s+([^,]+)", re.IGNORECASE
)


def tidy_address(value: Any) -> str:
    """Убирает из адреса административный шум, оставляя один читаемый адрес."""
    text = clean_text(value)
    if not text:
        return ""
    text = _INNER_OKRUG_RE.sub("", text)
    text = _INNER_CITY_RE.sub(lambda match: f", г. {match.group(1).strip()}", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    return text.strip(" ,")


# Организационно-правовые формы: полное написание -> аббревиатура. Порядок
# проверки — от длинной формы к короткой, иначе «Закрытое акционерное общество»
# схлопнулось бы по вхождению «акционерное общество».
_LEGAL_FORMS: tuple[tuple[str, str], ...] = (
    ("общество с ограниченной ответственностью", "ООО"),
    ("публичное акционерное общество", "ПАО"),
    ("непубличное акционерное общество", "НАО"),
    ("закрытое акционерное общество", "ЗАО"),
    ("открытое акционерное общество", "ОАО"),
    ("акционерное общество", "АО"),
    ("автономная некоммерческая организация", "АНО"),
    ("федеральное государственное унитарное предприятие", "ФГУП"),
    ("государственное унитарное предприятие", "ГУП"),
    ("муниципальное унитарное предприятие", "МУП"),
    ("федеральное государственное бюджетное учреждение", "ФГБУ"),
    ("государственное бюджетное учреждение", "ГБУ"),
    ("муниципальное бюджетное учреждение", "МБУ"),
    ("индивидуальный предприниматель", "ИП"),
)
_LEGAL_FORMS_SORTED = tuple(sorted(_LEGAL_FORMS, key=lambda pair: -len(pair[0])))

# Устойчивые обороты внутри названия — сокращаем только однозначные.
_INNER_ABBR: tuple[tuple[str, str], ...] = (
    ("научно-производственное объединение", "НПО"),
    ("научно-производственное предприятие", "НПП"),
    ("научно-исследовательский институт", "НИИ"),
    ("научно-технический центр", "НТЦ"),
    ("проектно-конструкторское бюро", "ПКБ"),
    ("управляющая компания", "УК"),
)


def _strip_legal_form(name: str) -> tuple[str, str]:
    """Отрезает ОПФ в начале названия -> (аббревиатура, остаток)."""
    lowered = name.lower()
    for full, abbr in _LEGAL_FORMS_SORTED:
        if lowered.startswith(full):
            return abbr, name[len(full):].strip()
    return "", name


def shorten_company_name(value: Any) -> str:
    """«Акционерное общество "Абсолют"» -> «АО «Абсолют»».

    Аббревиатура ОПФ обязательна: по ней в отчёте видно, ООО это, АО или ИП.
    У предпринимателя ФИО сохраняется целиком. Название без известной ОПФ
    (Ассоциация, Союз, Фонд) остаётся как есть.
    """
    text = clean_text(value)
    if not text:
        return ""
    text = text.replace("\u201c", "«").replace("\u201d", "»")
    text = re.sub(r'"([^"]*)"', "«\\1»", text)

    abbr, rest = _strip_legal_form(text)
    if abbr:
        # Форма могла повториться внутри — «АО «Акционерное общество …»».
        inner_abbr, inner_rest = _strip_legal_form(rest)
        if inner_abbr == abbr:
            rest = inner_rest
        text = f"{abbr} {rest}".strip() if rest else abbr

    for full, short in _INNER_ABBR:
        text = re.sub(re.escape(full), short, text, flags=re.IGNORECASE)
    return text


def looks_like_address(value: Any) -> bool:
    """Похоже ли значение на почтовый адрес."""
    text = clean_text(value)
    if len(text) < 10:
        return False
    lowered = text.lower().replace("ё", "е")
    hits = sum(1 for marker in _ADDRESS_MARKERS if marker in lowered)
    if _POSTAL_INDEX_RE.search(text):
        hits += 2
    return hits >= 2


def looks_like_fio(value: Any) -> bool:
    """Похоже ли значение на ФИО физического лица."""
    text = clean_text(value)
    return bool(text) and bool(_FIO_RE.fullmatch(text) or _FIO_RE.match(text))


def extract_fio(value: Any) -> str:
    """Достаёт первое встреченное ФИО из текста (или пустую строку)."""
    match = _FIO_RE.search(clean_text(value))
    return match.group(0).strip() if match else ""


#: Слова, с которых начинается должность руководителя. Подобраны так, чтобы не
#: совпасть с фамилией: «Глава» — только в этой форме, иначе под правило попал
#: бы, например, «Главин».
_POSITION_WORDS: tuple[str, ...] = (
    r"врио", r"и\.?\s?о\.?", r"исполняющ\w+\s+обязанност\w+",
    r"единоличн\w+\s+исполнительн\w+\s+орган\w*",
    r"генеральн\w+", r"исполнительн\w+", r"финансов\w+", r"коммерческ\w+",
    r"техническ\w+", r"главн\w+", r"управляющ\w+", r"конкурсн\w+",
    r"директор\w*", r"руководител\w*", r"президент\w*", r"председател\w*",
    r"правлени\w*", r"начальник\w*", r"глав[аы]", r"ликвидатор\w*",
    r"индивидуальн\w+", r"предпринимател\w*", r"учредител\w*",
)

_POSITION_PREFIX_RE = re.compile(
    r"^\s*(?:" + "|".join(_POSITION_WORDS) + r")\s*[:\-–—,]?\s*",
    re.IGNORECASE,
)


def director_fio(value: Any) -> str:
    """
    Оставляет от значения только ФИО руководителя, отбрасывая должность.

    Источники записывают руководителя по-разному: ``"Генеральный директор:
    Иванов И.И."``, ``"Директор Хватынец Леонид Витальевич"``, просто
    ``"Петров Пётр Петрович"``. В отчёте нужна фамилия с именем — к человеку
    обращаются при звонке, должность для этого не нужна.

    Должность срезается только тогда, когда из остатка получается опознаваемое
    ФИО. Иначе возвращается исходное значение: потерять данные хуже, чем
    оставить лишнее слово. Так, фамилия «Главин» не будет принята за «глава».
    """
    text = clean_text(value)
    if not text:
        return ""

    # «Должность: ФИО» — после двоеточия почти всегда уже чистое ФИО.
    if ":" in text:
        text = text.rsplit(":", 1)[-1].strip()

    # Срезаем должность по словам: «Врио генерального директора Иванов И.И.».
    stripped = text
    for _ in range(4):
        shorter = _POSITION_PREFIX_RE.sub("", stripped, count=1).strip(" :,-–—")
        if not shorter or shorter == stripped:
            break
        stripped = shorter

    return extract_fio(stripped) or extract_fio(text) or text


# --------------------------------------------------------------------------- #
#                              Прочие помощники                                #
# --------------------------------------------------------------------------- #

def join_unique(values: Iterable[Any], separator: str = "; ", limit: int | None = None) -> str:
    """Склеивает значения в строку, убирая дубли и пустые элементы, сохраняя порядок."""
    seen: list[str] = []
    for value in values:
        text = clean_text(value)
        if text and text not in seen:
            seen.append(text)
            if limit and len(seen) >= limit:
                break
    return separator.join(seen)


def merge_unique(target: list[str], extra: Iterable[str]) -> list[str]:
    """Добавляет в список ``target`` элементы ``extra``, пропуская дубли и пустые."""
    for value in extra:
        text = clean_text(value)
        if text and text not in target:
            target.append(text)
    return target


def truncate(text: str, max_length: int = 32000) -> str:
    """
    Обрезает строку до предела ячейки Excel (32767 символов).

    Excel не умеет хранить более длинные значения — обрезаем заранее,
    чтобы запись отчёта не падала на «толстых» полях.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
