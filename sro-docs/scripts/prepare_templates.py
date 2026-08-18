# -*- coding: utf-8 -*-
"""Разметка бланков СРО: пропуски «_____» → переменные {{...}}.

    python scripts/prepare_templates.py            # все СРО
    python scripts/prepare_templates.py СФЕРА-А    # только одна

Бланки приходят как пустые формы с подчёркиваниями, поэтому разметка
делается хирургически: каждая правка адресуется абзацем и либо номером
фрагмента, либо его текстом, и сверяется с ожидаемым содержимым.

Скрипт нужен только для тех бланков, что размечены здесь. Для нового
документа так делать не обязательно: откройте бланк в Word и впишите
переменные вида {{inn}} руками — программа их поймёт.

Что делает:
  * читает нетронутые оригиналы из sro/<СРО>/templates/_originals/;
  * применяет правки;
  * пишет результат в sro/<СРО>/templates/.

Почему так, а не «найти и заменить»: каждая операция сверяется с ожидаемым
исходным текстом. Если СРО изменит бланк, скрипт остановится с понятным
сообщением, а не молча испортит документ.

Всё остальное (стили, шрифты, таблицы, колонтитулы, поля страницы, тема,
нумерация) переносится из оригинала байт в байт — эти части ZIP-архива
просто копируются.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.docx_engine import W, _iter_paragraphs, _own_text_nodes  # noqa: E402

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class PrepareError(Exception):
    pass


# ============================================================ операции
def op_text(paragraph: int, node: int, expected: str, new: str) -> dict:
    """Заменить текст фрагмента №node в абзаце №paragraph."""
    return {"kind": "text", "p": paragraph, "n": node, "expected": expected, "new": new}


def op_cell(table: int, row: int, col: int, expected: str, new: str) -> dict:
    """Заменить текст ячейки таблицы (в т.ч. пустой — фрагмент будет создан)."""
    return {"kind": "cell", "t": table, "r": row, "c": col, "expected": expected, "new": new}


def op_mark(table: int, row: int, col: int, expected: str, new: str,
            size: int = 32) -> dict:
    """Ячейка под отметку «V»: крупно, жирно и ровно по центру.

    В бланке ячейки, где отметка уже стояла, оформлены крупно и по центру,
    а пустые — нет. Отметка, попавшая в пустую ячейку, выходила мелкой
    и прижатой к верху. Эта правка приводит все такие ячейки к одному виду:
    выравнивание по центру по горизонтали и вертикали, размер как у уже
    проставленных отметок, лишние пустые абзацы убираются.

    `size` — в полуточках, как принято в Word: 32 = 16 пт, 36 = 18 пт.
    """
    return {"kind": "mark", "t": table, "r": row, "c": col,
            "expected": expected, "new": new, "size": size}


def op_rel(old_target: str, new_target: str) -> dict:
    """Заменить адрес гиперссылки в word/_rels/document.xml.rels."""
    return {"kind": "rel", "expected": old_target, "new": new_target}


def op_font(paragraph: int, node: int, like_node: int) -> dict:
    """Дать фрагменту такое же оформление, как у другого фрагмента абзаца.

    В бланке некоторые пропуски («_____» для адресов) не имеют настроек
    шрифта вообще, поэтому подставленный текст выходил шрифтом по умолчанию
    (Calibri), а не Times New Roman, как весь документ.
    """
    return {"kind": "font", "p": paragraph, "n": node, "like": like_node}


def op_spacing(paragraph: int, attrs: dict) -> dict:
    """Задать интервалы абзаца (w:spacing), убрав всё остальное.

    Нужно, чтобы убрать «автоматический интервал» (beforeAutospacing),
    из-за которого текст в соседних ячейках таблицы стоял на разной высоте.
    """
    return {"kind": "spacing", "p": paragraph, "attrs": attrs}


def op_find(paragraph: int, expected: str, new: str) -> dict:
    """Заменить фрагмент, найденный по его ТЕКСТУ, а не по номеру.

    Устойчивее op_text: Word дробит текст по-разному в похожих бланках,
    и номера фрагментов «съезжают». Текст при этом остаётся тем же.
    Если такой текст встречается в абзаце не один раз — это ошибка,
    скрипт остановится.
    """
    return {"kind": "find", "p": paragraph, "expected": expected, "new": new}


def op_regex(paragraph: int, pattern: str, replacement: str,
             tab_pos: int | None = None) -> dict:
    """Переписать текст ВСЕГО абзаца по образцу.

    Работает только там, где весь абзац оформлен одинаково: текст
    собирается в строку, применяется замена, результат кладётся в первый
    фрагмент. Если оформление внутри абзаца разное (например, часть текста
    жирная), скрипт остановится — иначе потерялось бы выделение.

    Символ \t в замене превращается в настоящую табуляцию. Вместе с
    `tab_pos` (позиция в твипах) это заменяет «подложку из пробелов»:
    правая часть строки прижимается к полю и не съезжает, какой бы
    длины ни оказался подставленный текст.
    """
    return {"kind": "regex", "p": paragraph, "pattern": pattern,
            "replacement": replacement, "tab_pos": tab_pos}


def op_blank(paragraph, nodes: list[int] | None, new: str) -> dict:
    """Пропуск «______» заменить значением, не считая подчёркивания вручную.

    Проверяет, что перечисленные фрагменты состоят ТОЛЬКО из подчёркиваний
    (и пробелов), кладёт значение в первый, остальные вычищает. Точное число
    подчёркиваний в бланке значения не имеет и в разметке не фиксируется —
    иначе правка ломалась бы от одного лишнего знака.

    `nodes=None` — найти пропуски в абзаце самому. Удобно там, где подпись
    к строке и сама строка лежат в одном абзаце.
    """
    return {"kind": "blank", "p": paragraph, "nodes": nodes, "new": new}


def op_pad(paragraph: int, nodes: list[int], position: int) -> dict:
    """Подложку из пробелов заменить табуляцией с прижимом вправо.

    В отличие от op_tab не требует перечислять пробелы буквально: проверяет,
    что перечисленные фрагменты состоят ТОЛЬКО из пробелов, и заменяет их
    табуляцией. Подходит абзацам с неоднородным оформлением, где op_regex
    применять нельзя.
    """
    return {"kind": "pad", "p": paragraph, "nodes": nodes, "pos": position}


def op_rstrip(paragraph: int, node: int, prefix: str) -> dict:
    """Убрать «хвост» из пробелов у фрагмента, оставив нужный текст.

    Проверяет, что фрагмент — это `prefix` плюс только пробелы.
    """
    return {"kind": "rstrip", "p": paragraph, "n": node, "prefix": prefix}


def op_tab(paragraph: int, nodes: list[int], expected: list[str], position: int) -> dict:
    """Заменить «пробельную» подложку табуляцией с прижимом вправо.

    Так подпись руководителя всегда встаёт к правому полю, и между
    наименованием компании и инициалами остаётся место, чтобы расписаться.
    """
    return {"kind": "tab", "p": paragraph, "nodes": nodes,
            "expected": expected, "pos": position}


# ============================================================ ЗАЯВЛЕНИЕ
APPLICATION_OPS: list[dict] = [
    # --- шапка: дата документа ---
    op_text(4, 3, "__", "{{doc_day}}"),
    op_text(4, 4, "___", ""),
    op_text(4, 6, "_________", "{{doc_month_name}}"),
    op_text(4, 8, "20", "{{doc_year}}"),
    op_text(4, 9, "2", ""),
    op_text(4, 10, "6", ""),

    # --- п.1 ИНН: по одной цифре в клетке (таблица №2, 10 клеток) ---
    *[op_cell(2, 0, i, "", "{{inn_d%d}}" % (i + 1)) for i in range(10)],

    # --- п.2 ОГРН: 13 клеток (таблица №3) ---
    *[op_cell(3, 0, i, "", "{{ogrn_d%d}}" % (i + 1)) for i in range(13)],

    # --- п.3 наименования ---
    op_text(43, 0, "Общество с ограниченной ответственностью «", "{{legal_form_full}} «"),
    op_text(43, 1, "            ", "{{company_name_bare}}"),
    op_text(43, 3, "; ООО «", "; {{legal_form_short}} «"),
    op_text(43, 4, "                        ", "{{short_name_bare}}"),

    # --- п.4 юридический адрес ---
    op_text(45, 3,
            "___________________________________________________________________________________",
            "{{legal_address}}"),

    # --- п.5 фактический адрес ---
    op_text(47, 3,
            "____________________________________________________________________________________",
            "{{actual_address}}"),

    # --- п.6 контактные данные ---
    op_text(49, 3, "Генеральный директор ", "{{director_position}} "),
    op_text(49, 5, "________________________________", "{{director_full_name}}"),
    op_text(51, 2, "__________________", "{{phone}}"),
    op_text(51, 9, "_______________________", "{{email}}"),

    # --- п.7 виды объектов (таблица №4, столбец «отметить знаком V») ---
    op_mark(4, 1, 1, "V", "{{mark_object_ordinary}}", size=32),
    op_mark(4, 2, 1, "", "{{mark_object_hazardous}}", size=32),
    op_mark(4, 3, 1, "", "{{mark_object_nuclear}}", size=32),

    # --- п.8 уровень ответственности, КФ возмещения вреда (таблица №5) ---
    op_mark(5, 1, 3, "v", "{{mark_harm_level1}}", size=36),
    op_mark(5, 2, 3, "", "{{mark_harm_level2}}", size=36),
    op_mark(5, 3, 3, "", "{{mark_harm_level3}}", size=36),
    op_mark(5, 4, 3, "", "{{mark_harm_level4}}", size=36),
    op_mark(5, 5, 3, "", "{{mark_harm_level5}}", size=36),

    # --- п.9 уровень ответственности, КФ обеспечения дог. обязательств (таблица №6) ---
    op_mark(6, 1, 3, "", "{{mark_contract_level1}}", size=36),
    op_mark(6, 2, 3, "", "{{mark_contract_level2}}", size=36),
    op_mark(6, 3, 3, "", "{{mark_contract_level3}}", size=36),
    op_mark(6, 4, 3, "", "{{mark_contract_level4}}", size=36),
    op_mark(6, 5, 3, "", "{{mark_contract_level5}}", size=36),

    # --- подпись ---
    op_text(125, 0, "Генеральный директор ", "{{director_position}} "),
    op_text(125, 1, "ООО ", "{{legal_form_short}} "),
    op_text(125, 3, "_____________   ", "{{short_name_bare}}"),
    op_text(125, 9, "___________________", "{{director_short_name}}"),
    op_text(125, 10, ".", ""),

    # --- чужая почта, оставшаяся в гиперссылке от прошлой компании ---
    op_rel("mailto:regionrem@mail.ru", "mailto:{{email}}"),

    # ---------------- правки вёрстки бланка ----------------

    # Шапка: у правой ячейки («В Ассоциацию…») включён автоматический
    # интервал, из-за него адресат стоял на строку ниже номера заявления.
    # Приводим к тем же интервалам, что у левой ячейки.
    op_spacing(5, {"after": "0", "line": "240", "lineRule": "auto"}),
    op_spacing(6, {"after": "0", "line": "240", "lineRule": "auto"}),

    # Пропуски для адресов не имели настроек шрифта — подставленный текст
    # выходил шрифтом Calibri вместо Times New Roman, как весь документ.
    op_font(45, 3, 0),
    op_font(47, 3, 0),

    # Подпись: вместо подложки из пробелов — табуляция с прижимом к правому
    # полю, чтобы между наименованием и инициалами было место расписаться.
    op_tab(125, [5, 6], ["                           ", " "], 9356),
]

# ============================================================ ДОВЕРЕННОСТЬ
POWER_OPS: list[dict] = [
    # --- шапка бланка ---
    op_text(2, 0, "ООО ", "{{legal_form_short}} "),
    op_text(2, 2, "________", "{{short_name_bare}}"),

    # --- дата ---
    op_text(6, 1, "_", "{{doc_day}}"),
    op_text(6, 2, "____", ""),
    # В бланке между пропуском для месяца и «2026» нет пробела
    # («______________2026 г.») — добавляем его вместе с месяцем.
    op_text(6, 4, "_____", "{{doc_month_name}} "),
    op_text(6, 5, "_________", ""),
    op_text(6, 6, "20", "{{doc_year}}"),
    op_text(6, 7, "2", ""),
    op_text(6, 8, "6 ", " "),

    # --- номер доверенности ---
    op_text(8, 1, "№ ", "№ {{power_number}}"),

    # --- преамбула: кто выдаёт доверенность ---
    op_text(10, 0, "Общество с ограниченной", "{{legal_form_full}}"),
    op_text(10, 1, " ответственностью ", " "),
    op_text(10, 2, "«»", "«{{company_name_bare}}»"),
    op_text(10, 6, "__________", "{{inn}}"),
    op_text(10, 9, "Генерального директора", "{{director_position_genitive}}"),
    op_text(10, 13, "_____________", "{{director_full_name_genitive}}"),
    op_text(10, 18, "на основании Устава, ", "на основании {{director_basis_genitive}}, "),

    # --- доверенное лицо (представитель Ассоциации, задаётся в config/attorney.json) ---
    op_text(11, 0, "Кодловского", "{{attorney_full_name_genitive}}"),
    op_text(11, 1, " Максима Анатольевича", ""),
    op_text(11, 3, "01", "{{attorney_birth_date}}"),
    op_text(11, 4, ".", ""),
    op_text(11, 5, "0", ""),
    op_text(11, 6, "7", ""),
    op_text(11, 7, ".198", ""),
    op_text(11, 8, "1 ", " "),
    op_text(11, 9, "г.р., место рождения: г", "г.р., место рождения: "),
    op_text(11, 10, "ор", ""),
    op_text(11, 11, ".", ""),
    op_text(11, 12, " ", ""),
    op_text(11, 13, "Мурманск", "{{attorney_birth_place}}"),
    op_text(11, 14, ", паспорт 4", ", паспорт "),
    op_text(11, 15, "1", "{{attorney_passport}}"),
    op_text(11, 16, " ", ""),
    op_text(11, 17, "26", ""),
    op_text(11, 18, " ", ""),
    op_text(11, 19, "679289", ""),
    op_text(11, 21, "дан", "дан "),
    op_text(11, 22, " ", ""),
    op_text(11, 23,
            "ГУ МВД России по г. Санкт-Петербургу и Ленинградской области 15",
            "{{attorney_passport_issued_by}} {{attorney_passport_date}}"),
    op_text(11, 24, ".", ""),
    op_text(11, 25, "0", ""),
    op_text(11, 26, "7", ""),
    op_text(11, 27, ".20", ""),
    op_text(11, 28, "26", ""),
    op_text(11, 32, "470-004", "{{attorney_dept_code}}"),
    op_text(11, 35, " по адресу:", " по адресу: "),
    op_text(11, 36, " Мурманская обл., ", ""),
    op_text(11, 37, "г. Мурманск, ул. Маяковского д.1 кв.36", "{{attorney_reg_address}}"),

    # --- подпись доверенного лица ---
    op_text(17, 7, "Кодловский", "{{attorney_short_name}}"),
    op_text(17, 8, " М.А", ""),
    op_text(17, 9, ".", ""),

    # --- подпись руководителя ---
    op_text(20, 0, "Генеральный директор", "{{director_position}}"),
    op_text(21, 0, "ООО ", "{{legal_form_short}} "),
    op_text(21, 2, "________", "{{short_name_bare}}"),
    op_text(21, 3, "_", ""),
    op_text(21, 12, "_______", "{{director_short_name}}"),
    op_text(21, 13, "_______/", "/"),
]

# ============================================================ ДОВЕРЕННОСТЬ «СФЕРЫ»
# Три «СФЕРЫ» устроены одинаково: те же абзацы, тот же текст, различаются
# только названием СРО. Поэтому разметка у них общая.
# Адресуемся текстом (op_find) и образцом (op_regex), а не номерами
# фрагментов: Word дробит одинаковый текст в этих файлах по-разному.
SFERA_POWER_OPS: list[dict] = [
    # --- шапка бланка ---
    op_regex(0, r"^ООО «_+»$", "{{legal_form_short}} «{{short_name_bare}}»"),

    # --- дата и место составления ---
    # Дата слева, город справа. В бланке они разведены подложкой из пробелов,
    # рассчитанной на короткое «_» ______ 2025. Настоящая дата длиннее,
    # и город уезжал на вторую строку — заменяем подложку табуляцией
    # с прижимом к правому полю.
    op_regex(4,
             r"^«_» ______ 2025 г\.\s+г\. Санкт-Петербург$",
             "«{{doc_day}}» {{doc_month_name}} {{doc_year}} г.\tг. {{sro_city}}",
             tab_pos=9355),

    # --- преамбула: кто выдаёт доверенность ---
    # Абзац оформлен неоднородно (наименование жирное), поэтому по фрагментам.
    op_text(8, 0, "Общество с ограниченной", "{{legal_form_full}}"),
    op_text(8, 1, " ответственностью ", " "),
    op_text(8, 2, "«»", "«{{company_name_bare}}»"),
    op_text(8, 6, "__________", "{{inn}}"),
    op_text(8, 9, "Генерального директора", "{{director_position_genitive}}"),
    op_text(8, 13, "_____________", "{{director_full_name_genitive}}"),
    op_find(8, "на основании Устава, ",
            "на основании {{director_basis_genitive}}, "),

    # --- доверенное лицо: весь абзац одним образцом ---
    op_regex(
        9,
        r"^Корневу Юлию Юрьевну, .*кв\.39,$",
        "{{attorney_full_name_genitive}}, {{attorney_birth_date}}г.р., "
        "место рождения: {{attorney_birth_place}}, "
        "паспорт {{attorney_passport}}, выдан {{attorney_passport_issued_by}} "
        "{{attorney_passport_date}} года, "
        "код подразделения: {{attorney_dept_code}}, "
        "{{attorney_registered_word}} по адресу: {{attorney_reg_address}},"),

    # --- подпись доверенного лица ---
    op_regex(15, r"/Корнева Ю\.Ю\./$", "/{{attorney_short_name}}/"),

    # --- подпись руководителя ---
    op_regex(18, r"^Генеральный директор$", "{{director_position}}"),
    op_regex(19, r"^ООО «_+»(\s+_+\s+)_+(\s*)$",
             r"{{legal_form_short}} «{{short_name_bare}}»\1{{director_short_name}}\2"),
]


# ============================================================ ЗАЯВЛЕНИЕ «СФЕРЫ»
def sfera_application_ops(levels: int) -> list[dict]:
    """Разметка заявления «СФЕР». `levels` — сколько уровней ответственности.

    У СФЕРА-А (строительство) их пять, у изыскателей и проектировщиков —
    четыре. Всё остальное в трёх бланках совпадает, поэтому разметка общая,
    а подпись ищется по тексту: из-за разного числа строк в таблицах
    номера последних абзацев съезжают.
    """
    return [
        # --- шапка: исходящий номер и дата ---
        op_regex(r"^№__от «_____» ___________20__ г\.$",
                 r"^№__от «_____» ___________20__ г\.$",
                 "№ {{doc_number}} от «{{doc_day}}» {{doc_month_name}} "
                 "{{doc_year}} г."),

        # --- п.1 ИНН и п.2 ОГРН: по одной цифре в клетке ---
        *[op_cell(1, 0, i, "", "{{inn_d%d}}" % (i + 1)) for i in range(10)],
        *[op_cell(2, 0, i, "", "{{ogrn_d%d}}" % (i + 1)) for i in range(13)],

        # --- п.3 наименование ---
        op_regex(38, r"дата его рождения_+$",
                 "дата его рождения {{company_full_name}}"),

        # --- п.4 юридический адрес: две отдельные строки ---
        # Бланк просит адрес двумя строками: сверху индекс, регион, город
        # и улица, снизу — дом, корпус, офис. Делим по указателю дома.
        op_regex(40, r"^_+$", "{{legal_address_street}}"),
        op_blank(42, None, "{{legal_address_house}}"),

        # --- п.5 и п.6: адрес целиком одной строкой ---
        # Здесь бланк устроен иначе: подпись к строке и вторая строка лежат
        # в ОДНОМ абзаце, и «дом 35…» прилипал бы к концу подписи. Поэтому
        # пишем адрес целиком в первую строку, вторую оставляем пустой.
        op_regex(45, r"^_+$", "{{actual_address}}"),
        op_blank(46, None, ""),
        op_regex(48, r"^_+$", "{{postal_address}}"),
        op_blank(49, None, ""),

        # --- п.7 контакты: строка руководителя и строка контактного лица ---
        op_regex(52, r"^_+$", "{{director_contact_line}}"),
        # В этом абзаце подпись к строке набрана другим шрифтом, чем сама
        # строка, поэтому переписываем только фрагменты с подчёркиваниями.
        op_blank(53, [10, 11, 12], "{{director_contact_line}}"),

        # --- п.8 виды объектов ---
        op_mark(3, 1, 1, "", "{{mark_object_ordinary}}", size=32),
        op_mark(3, 2, 1, "", "{{mark_object_hazardous}}", size=32),
        op_mark(3, 3, 1, "", "{{mark_object_nuclear}}", size=32),

        # --- п.9 и п.10 уровни ответственности ---
        *[op_mark(4, n, 3, "", "{{mark_harm_level%d}}" % n, size=36)
          for n in range(1, levels + 1)],
        *[op_mark(5, n, 3, "", "{{mark_contract_level%d}}" % n, size=36)
          for n in range(1, levels + 1)],

        # --- подпись (номер абзаца зависит от числа уровней — ищем по тексту) ---
        op_regex(r"^Подпись уполномоченного лица организации",
                 r"/_+/$", "/{{director_short_name}}/"),
    ]


# ============================================================ ДОВЕРЕННОСТЬ ЯРД
# Устроена иначе, чем «СФЕРЫ»: срок три года, город составления пустой,
# ИНН обозначен пробелами, а не подчёркиваниями.
YARD_POWER_OPS: list[dict] = [
    # --- шапка бланка ---
    op_text(0, 0, "ООО ", "{{legal_form_short}} "),
    op_text(0, 2, "_____________", "{{short_name_bare}}"),

    # --- дата слева, город справа (подложку из пробелов → табуляция) ---
    op_text(4, 1, "_____", "{{doc_day}}"),
    op_text(4, 3, "________", "{{doc_month_name}}"),
    op_text(4, 4, " 2024", " {{doc_year}}"),
    op_rstrip(4, 6, "г."),
    op_pad(4, [7, 8, 9], 9355),
    op_text(4, 10, "     г. ", "г. "),
    op_text(4, 11, "_____________", "{{sro_city}}"),

    # --- преамбула ---
    op_text(8, 0, "Общество с ограниченной ответственностью ", "{{legal_form_full}} "),
    op_text(8, 2, "  ", "{{company_name_bare}}"),
    op_text(8, 3, "                   ", ""),
    op_text(8, 4, "                           ", ""),
    op_text(8, 5, "      ", ""),
    op_text(8, 9, " ИНН       ", " ИНН {{inn}}"),
    op_text(8, 12, "Генерального директора", "{{director_position_genitive}}"),
    op_text(8, 15, " _____________________________________________",
            " {{director_full_name_genitive}}"),
    op_find(8, "на основании Устава, ",
            "на основании {{director_basis_genitive}}, "),

    # --- доверенное лицо ---
    op_regex(
        9,
        r"^Жирихова Андрея Валерьевича, .*кв\. 41,$",
        "{{attorney_full_name_genitive}}, {{attorney_birth_date}}г.р., "
        "место рождения: {{attorney_birth_place}}, "
        "паспорт {{attorney_passport}}, выдан {{attorney_passport_issued_by}} "
        "{{attorney_passport_date}} года, "
        "код подразделения: {{attorney_dept_code}}, "
        "{{attorney_registered_word}} по адресу: {{attorney_reg_address}},"),

    # --- подписи ---
    op_regex(15, r"/Жирихов А\.В\./$", "/{{attorney_short_name}}/"),
    op_regex(18, r"^Генеральный директор$", "{{director_position}}"),
    op_regex(19, r"^ООО «\s+»(\s+_+\s+)/\s*Ф\.И\.О\.\s*/ ?$",
             r"{{legal_form_short}} «{{short_name_bare}}»\1/{{director_short_name}}/ "),
]


# ============================================================ реестр бланков
# СРО → список (файл-оригинал, как назвать результат, правки)
TEMPLATES: dict[str, list[tuple]] = {
    "СССС": [
        ("Заявление_о_вступлении_ОРИГИНАЛ.docx",
         "01_Заявление_о_вступлении.docx", APPLICATION_OPS),
        ("Доверенность_ОРИГИНАЛ.docx", "02_Доверенность.docx", POWER_OPS),
    ],
    "СФЕРА-А": [
        ("Заявление_ОРИГИНАЛ.docx", "01_Заявление.docx", sfera_application_ops(5)),
        ("Доверенность_ОРИГИНАЛ.docx", "02_Доверенность.docx", SFERA_POWER_OPS),
    ],
    "СФЕРА ИЗЫСКАТЕЛЕЙ": [
        ("Заявление_ОРИГИНАЛ.docx", "01_Заявление.docx", sfera_application_ops(4)),
        ("Доверенность_ОРИГИНАЛ.docx", "02_Доверенность.docx", SFERA_POWER_OPS),
    ],
    "СФЕРА ПРОЕКТИРОВЩИКОВ": [
        ("Заявление_ОРИГИНАЛ.docx", "01_Заявление.docx", sfera_application_ops(4)),
        ("Доверенность_ОРИГИНАЛ.docx", "02_Доверенность.docx", SFERA_POWER_OPS),
    ],
    "ЯРД": [
        ("Доверенность_ОРИГИНАЛ.docx", "02_Доверенность.docx", YARD_POWER_OPS),
    ],
}


# ============================================================ реализация
def _style_key(node) -> str:
    """Отпечаток оформления фрагмента — чтобы понять, однороден ли абзац."""
    run_properties = node.getparent().find(W + "rPr")
    if run_properties is None:
        return "<без оформления>"
    xml = etree.tostring(run_properties, encoding="unicode")
    return re.sub(r'\sw:rsid[A-Za-z]*="[^"]*"', "", xml)


def _locate_cell(tables, op, label):
    """Найти ячейку таблицы по номерам, с понятной ошибкой."""
    if op["t"] >= len(tables):
        raise PrepareError(
            f"{label}: в документе нет таблицы №{op['t']} (всего {len(tables)}).")
    rows = list(tables[op["t"]].findall(W + "tr"))
    if op["r"] >= len(rows):
        raise PrepareError(
            f"{label}: в таблице №{op['t']} нет строки №{op['r']}.")
    cells = list(rows[op["r"]].findall(W + "tc"))
    if op["c"] >= len(cells):
        raise PrepareError(
            f"{label}: в таблице №{op['t']}, строке №{op['r']} "
            f"нет ячейки №{op['c']}.")
    return cells[op["c"]]


def _center_cell(cell) -> None:
    """Выравнивание содержимого ячейки по центру по вертикали."""
    tc_pr = cell.find(W + "tcPr")
    if tc_pr is None:
        tc_pr = etree.Element(W + "tcPr")
        cell.insert(0, tc_pr)
    existing = tc_pr.find(W + "vAlign")
    if existing is not None:
        tc_pr.remove(existing)
    align = etree.SubElement(tc_pr, W + "vAlign")
    align.set(W + "val", "center")


def _center_paragraph(paragraph) -> None:
    """Выравнивание абзаца по центру, без отступов."""
    p_pr = paragraph.find(W + "pPr")
    if p_pr is None:
        p_pr = etree.Element(W + "pPr")
        paragraph.insert(0, p_pr)
    for tag in ("ind", "jc"):
        existing = p_pr.find(W + tag)
        if existing is not None:
            p_pr.remove(existing)
    jc = etree.SubElement(p_pr, W + "jc")
    jc.set(W + "val", "center")


def _emphasize(node, size: int) -> None:
    """Сделать фрагмент жирным и заданного размера."""
    run = node.getparent()
    r_pr = run.find(W + "rPr")
    if r_pr is None:
        r_pr = etree.Element(W + "rPr")
        run.insert(0, r_pr)
    for tag in ("b", "bCs", "sz", "szCs"):
        existing = r_pr.find(W + tag)
        if existing is not None:
            r_pr.remove(existing)
    etree.SubElement(r_pr, W + "b")
    etree.SubElement(r_pr, W + "bCs")
    for tag in ("sz", "szCs"):
        element = etree.SubElement(r_pr, W + tag)
        element.set(W + "val", str(size))


def _write_with_tabs(node, text: str) -> None:
    """Записать текст, превратив \t в настоящие табуляции внутри фрагмента."""
    parts = text.split("\t")
    run = node.getparent()
    _set_node_text(node, parts[0])
    position = list(run).index(node)
    for part in parts[1:]:
        position += 1
        run.insert(position, etree.Element(W + "tab"))
        position += 1
        extra = etree.Element(W + "t")
        _set_node_text(extra, part)
        run.insert(position, extra)


def _add_right_tab(paragraph, position: int) -> None:
    """Позиция табуляции с прижимом вправо. По схеме w:tabs идёт первым в pPr."""
    p_pr = paragraph.find(W + "pPr")
    if p_pr is None:
        p_pr = etree.Element(W + "pPr")
        paragraph.insert(0, p_pr)
    existing = p_pr.find(W + "tabs")
    if existing is not None:
        p_pr.remove(existing)
    tabs = etree.Element(W + "tabs")
    stop = etree.SubElement(tabs, W + "tab")
    stop.set(W + "val", "right")
    stop.set(W + "pos", str(position))
    p_pr.insert(0, tabs)


def _set_node_text(node, text: str) -> None:
    node.text = text
    node.set(XML_SPACE, "preserve")


def _cell_layout(cell):
    """Разбор ячейки: (весь текст, абзац-получатель, его фрагменты, прочие абзацы).

    Ячейка может состоять из нескольких абзацев (например, пустой + «V»).
    Значение пишем в тот абзац, где текст уже есть — у него нужное
    оформление (выравнивание по центру и т.п.). Если текста нет ни в одном,
    берём последний абзац.
    """
    paragraphs = list(cell.iter(W + "p"))
    if not paragraphs:
        raise PrepareError("В ячейке таблицы нет ни одного абзаца.")
    texts = ["".join(n.text or "" for n in _own_text_nodes(p)) for p in paragraphs]
    target_index = len(paragraphs) - 1
    for index, text in enumerate(texts):
        if text:
            target_index = index
            break
    others = [p for i, p in enumerate(paragraphs) if i != target_index]
    return ("".join(texts), paragraphs[target_index],
            _own_text_nodes(paragraphs[target_index]), others)


def _make_run(paragraph, text: str):
    """Создать фрагмент текста, унаследовав оформление от знака абзаца."""
    run = etree.SubElement(paragraph, W + "r")
    p_pr = paragraph.find(W + "pPr")
    if p_pr is not None:
        r_pr = p_pr.find(W + "rPr")
        if r_pr is not None:
            copied = etree.fromstring(etree.tostring(r_pr))
            # В rPr знака абзаца встречаются служебные пометки правок — уберём.
            for junk in list(copied):
                if junk.tag in (W + "ins", W + "del", W + "rPrChange"):
                    copied.remove(junk)
            run.append(copied)
    text_node = etree.SubElement(run, W + "t")
    _set_node_text(text_node, text)
    return run


def _resolve_paragraph(paragraphs, where, label: str) -> int:
    """Номер абзаца: либо задан числом, либо ищется по образцу текста.

    Поиск по тексту нужен там, где похожие бланки различаются числом строк
    в таблицах: у строительных СРО уровней пять, у проектных четыре, и все
    последующие абзацы съезжают. Текст при этом остаётся тем же.
    """
    if isinstance(where, int):
        return where
    pattern = re.compile(where)
    hits = [i for i, p in enumerate(paragraphs)
            if pattern.search("".join(n.text or "" for n in _own_text_nodes(p)))]
    if len(hits) != 1:
        raise PrepareError(
            f"{label}: абзац по образцу {where!r} найден {len(hits)} раз, "
            f"а нужен ровно один.\n"
            f"Шаблон изменился — обновите карту разметки в этом скрипте."
        )
    return hits[0]


def apply_ops(document_xml: bytes, ops: list[dict], label: str) -> bytes:
    root = etree.fromstring(document_xml)
    paragraphs = list(_iter_paragraphs(root))
    tables = list(root.iter(W + "tbl"))

    for op in ops:
        if "p" in op:
            op = dict(op, p=_resolve_paragraph(paragraphs, op["p"], label))
        if op["kind"] == "text":
            index, node_index = op["p"], op["n"]
            if index >= len(paragraphs):
                raise PrepareError(
                    f"{label}: в документе нет абзаца №{index} "
                    f"(всего {len(paragraphs)}). Шаблон изменился."
                )
            nodes = _own_text_nodes(paragraphs[index])
            if node_index >= len(nodes):
                raise PrepareError(
                    f"{label}: в абзаце №{index} нет фрагмента №{node_index} "
                    f"(всего {len(nodes)}). Шаблон изменился."
                )
            node = nodes[node_index]
            actual = node.text or ""
            if actual != op["expected"]:
                raise PrepareError(
                    f"{label}: абзац №{index}, фрагмент №{node_index}.\n"
                    f"  Ожидался текст: {op['expected']!r}\n"
                    f"  В документе:    {actual!r}\n"
                    f"Шаблон изменился — обновите карту разметки в этом скрипте."
                )
            _set_node_text(node, op["new"])

        elif op["kind"] == "mark":
            cells = _locate_cell(tables, op, label)
            actual, paragraph, nodes, others = _cell_layout(cells)
            if actual != op["expected"]:
                raise PrepareError(
                    f"{label}: таблица №{op['t']}, ячейка [{op['r']}][{op['c']}].\n"
                    f"  Ожидался текст: {op['expected']!r}\n"
                    f"  В документе:    {actual!r}\n"
                    f"Шаблон изменился — обновите карту разметки в этом скрипте."
                )
            _center_cell(cells)
            for stray in others:
                parent = stray.getparent()
                if parent is not None and not _own_text_nodes(stray):
                    parent.remove(stray)      # пустая строка сдвигала отметку вниз
            _center_paragraph(paragraph)
            if nodes:
                _set_node_text(nodes[0], op["new"])
                for extra in nodes[1:]:
                    _set_node_text(extra, "")
                _emphasize(nodes[0], op["size"])
            else:
                run = _make_run(paragraph, op["new"])
                _emphasize(run.find(W + "t"), op["size"])

        elif op["kind"] == "blank":
            nodes = _own_text_nodes(paragraphs[op["p"]])
            indices = op["nodes"]
            if indices is None:
                indices = [i for i, n in enumerate(nodes)
                           if (n.text or "") and not (n.text or "").strip(" _")]
                if not indices:
                    raise PrepareError(
                        f"{label}: в абзаце №{op['p']} не найдено пропусков "
                        f"из подчёркиваний. Шаблон изменился."
                    )
            picked = []
            for index in indices:
                if index >= len(nodes):
                    raise PrepareError(
                        f"{label}: в абзаце №{op['p']} нет фрагмента №{index} "
                        f"(всего {len(nodes)}). Шаблон изменился.")
                node = nodes[index]
                text = node.text or ""
                if not text or text.strip(" _"):
                    raise PrepareError(
                        f"{label}: абзац №{op['p']}, фрагмент №{index} — "
                        f"ожидался пропуск из подчёркиваний.\n"
                        f"  В документе: {text[:60]!r}\n"
                        f"Шаблон изменился — обновите карту разметки."
                    )
                picked.append(node)
            _set_node_text(picked[0], op["new"])
            for node in picked[1:]:
                _set_node_text(node, "")

        elif op["kind"] == "pad":
            paragraph = paragraphs[op["p"]]
            nodes = _own_text_nodes(paragraph)
            picked = [nodes[i] for i in op["nodes"]]
            bad = [(i, n.text) for i, n in zip(op["nodes"], picked)
                   if (n.text or "").strip()]
            if bad:
                raise PrepareError(
                    f"{label}: в абзаце №{op['p']} фрагменты {bad!r} — не пробелы.\n"
                    f"Шаблон изменился — обновите карту разметки в этом скрипте."
                )
            first = picked[0]
            run = first.getparent()
            run.insert(list(run).index(first), etree.Element(W + "tab"))
            for node in picked:
                _set_node_text(node, "")
            _add_right_tab(paragraph, op["pos"])

        elif op["kind"] == "rstrip":
            node = _own_text_nodes(paragraphs[op["p"]])[op["n"]]
            actual = node.text or ""
            if actual != op["prefix"] + actual[len(op["prefix"]):] or \
                    actual[len(op["prefix"]):].strip():
                raise PrepareError(
                    f"{label}: абзац №{op['p']}, фрагмент №{op['n']}.\n"
                    f"  Ожидалось {op['prefix']!r} и дальше только пробелы.\n"
                    f"  В документе: {actual!r}"
                )
            _set_node_text(node, op["prefix"])

        elif op["kind"] == "find":
            nodes = _own_text_nodes(paragraphs[op["p"]])
            hits = [n for n in nodes if (n.text or "") == op["expected"]]
            if len(hits) != 1:
                raise PrepareError(
                    f"{label}: в абзаце №{op['p']} фрагмент с текстом "
                    f"{op['expected']!r} найден {len(hits)} раз, а нужен ровно один.\n"
                    f"Шаблон изменился — обновите карту разметки в этом скрипте."
                )
            _set_node_text(hits[0], op["new"])

        elif op["kind"] == "regex":
            paragraph = paragraphs[op["p"]]
            nodes = _own_text_nodes(paragraph)
            if not nodes:
                raise PrepareError(f"{label}: абзац №{op['p']} пуст.")
            styles = {_style_key(n) for n in nodes}
            if len(styles) > 1:
                raise PrepareError(
                    f"{label}: абзац №{op['p']} оформлен неоднородно "
                    f"({len(styles)} вида оформления). Переписать его целиком нельзя — "
                    f"потеряется выделение. Используйте op_text или op_find."
                )
            joined = "".join(n.text or "" for n in nodes)
            new_text, count = re.subn(op["pattern"], op["replacement"], joined)
            if count == 0:
                raise PrepareError(
                    f"{label}: в абзаце №{op['p']} не найден образец "
                    f"{op['pattern']!r}.\n"
                    f"  В документе: {joined[:120]!r}\n"
                    f"Шаблон изменился — обновите карту разметки в этом скрипте."
                )
            for extra in nodes[1:]:
                _set_node_text(extra, "")
            if "\t" in new_text:
                _write_with_tabs(nodes[0], new_text)
                if op.get("tab_pos"):
                    _add_right_tab(paragraph, op["tab_pos"])
            else:
                _set_node_text(nodes[0], new_text)

        elif op["kind"] == "font":
            nodes = _own_text_nodes(paragraphs[op["p"]])
            source = nodes[op["like"]].getparent().find(W + "rPr")
            if source is None:
                raise PrepareError(
                    f"{label}: у фрагмента №{op['like']} абзаца №{op['p']} нет "
                    f"оформления, копировать нечего. Шаблон изменился."
                )
            run = nodes[op["n"]].getparent()
            existing = run.find(W + "rPr")
            if existing is not None:
                run.remove(existing)
            run.insert(0, etree.fromstring(etree.tostring(source)))

        elif op["kind"] == "spacing":
            paragraph = paragraphs[op["p"]]
            p_pr = paragraph.find(W + "pPr")
            if p_pr is None:
                raise PrepareError(
                    f"{label}: у абзаца №{op['p']} нет свойств. Шаблон изменился.")
            spacing = p_pr.find(W + "spacing")
            if spacing is None:
                spacing = etree.Element(W + "spacing")
                p_pr.insert(0, spacing)
            for name in list(spacing.attrib):
                del spacing.attrib[name]
            for name, value in op["attrs"].items():
                spacing.set(W + name, value)

        elif op["kind"] == "tab":
            paragraph = paragraphs[op["p"]]
            nodes = _own_text_nodes(paragraph)
            actual = [nodes[i].text or "" for i in op["nodes"]]
            if actual != op["expected"]:
                raise PrepareError(
                    f"{label}: абзац №{op['p']}, подложка подписи.\n"
                    f"  Ожидалось: {op['expected']!r}\n"
                    f"  В документе: {actual!r}\n"
                    f"Шаблон изменился — обновите карту разметки в этом скрипте."
                )
            p_pr = paragraph.find(W + "pPr")
            if p_pr is None:
                raise PrepareError(
                    f"{label}: у абзаца №{op['p']} нет свойств. Шаблон изменился.")
            # По схеме OOXML w:tabs идёт раньше w:spacing — вставляем первым.
            existing_tabs = p_pr.find(W + "tabs")
            if existing_tabs is not None:
                p_pr.remove(existing_tabs)
            tabs = etree.Element(W + "tabs")
            stop = etree.SubElement(tabs, W + "tab")
            stop.set(W + "val", "right")
            stop.set(W + "pos", str(op["pos"]))
            p_pr.insert(0, tabs)
            # Первый фрагмент подложки становится табуляцией, остальные пустеют.
            first = nodes[op["nodes"][0]]
            run = first.getparent()
            run.insert(list(run).index(first), etree.Element(W + "tab"))
            _set_node_text(first, "")
            for index in op["nodes"][1:]:
                _set_node_text(nodes[index], "")

        elif op["kind"] == "cell":
            t_index, row_index, col_index = op["t"], op["r"], op["c"]
            if t_index >= len(tables):
                raise PrepareError(
                    f"{label}: в документе нет таблицы №{t_index} "
                    f"(всего {len(tables)}). Шаблон изменился."
                )
            rows = list(tables[t_index].findall(W + "tr"))
            if row_index >= len(rows):
                raise PrepareError(
                    f"{label}: в таблице №{t_index} нет строки №{row_index}.")
            cells = list(rows[row_index].findall(W + "tc"))
            if col_index >= len(cells):
                raise PrepareError(
                    f"{label}: в таблице №{t_index}, строке №{row_index} "
                    f"нет ячейки №{col_index}.")
            actual, paragraph, nodes, others = _cell_layout(cells[col_index])
            if actual != op["expected"]:
                raise PrepareError(
                    f"{label}: таблица №{t_index}, ячейка [{row_index}][{col_index}].\n"
                    f"  Ожидался текст: {op['expected']!r}\n"
                    f"  В документе:    {actual!r}\n"
                    f"Шаблон изменился — обновите карту разметки в этом скрипте."
                )
            if nodes:
                _set_node_text(nodes[0], op["new"])
                for extra in nodes[1:]:
                    _set_node_text(extra, "")
            else:
                _make_run(paragraph, op["new"])
            for other in others:
                for extra in _own_text_nodes(other):
                    _set_node_text(extra, "")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def apply_rel_ops(rels_xml: bytes, ops: list[dict], label: str) -> bytes:
    text = rels_xml.decode("utf-8")
    for op in ops:
        if op["kind"] != "rel":
            continue
        if op["expected"] not in text:
            raise PrepareError(
                f"{label}: в связях документа не найден адрес {op['expected']!r}. "
                f"Шаблон изменился."
            )
        text = text.replace(op["expected"], op["new"])
    return text.encode("utf-8")


def prepare(source: Path, target: Path, ops: list[dict]) -> None:
    label = source.name
    has_rel_ops = any(op["kind"] == "rel" for op in ops)
    temp = target.with_suffix(".tmp")

    with zipfile.ZipFile(source, "r") as src, \
            zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as dst:
        names = src.namelist()
        if "word/document.xml" not in names:
            raise PrepareError(f"{label}: это не документ Word (.docx).")
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "word/document.xml":
                data = apply_ops(data, ops, label)
            elif item.filename == "word/_rels/document.xml.rels" and has_rel_ops:
                data = apply_rel_ops(data, ops, label)
            dst.writestr(item, data)

    temp.replace(target)


def main(argv: list[str] | None = None) -> int:
    from src.docx_engine import scan_placeholders

    argv = sys.argv[1:] if argv is None else argv
    wanted = argv[0] if argv else None
    if wanted and wanted not in TEMPLATES:
        print(f"Для СРО «{wanted}» разметка в этом скрипте не описана.")
        print("Описаны: " + ", ".join(f"«{k}»" for k in TEMPLATES))
        return 1

    print("Разметка бланков СРО")
    print("=" * 62)
    total = 0
    for sro, items in TEMPLATES.items():
        if wanted and sro != wanted:
            continue
        folder = ROOT / "sro" / sro / "templates"
        originals = folder / "_originals"
        if not originals.exists():
            print(f"\n{sro}: не найдена папка с оригиналами {originals}")
            return 1
        print(f"\n{sro}")
        for source_name, target_name, ops in items:
            source = originals / source_name
            if not source.exists():
                print(f"  ПРОПУЩЕН: не найден оригинал {source_name}")
                continue
            try:
                prepare(source, folder / target_name, ops)
            except PrepareError as exc:
                print(f"\n  ОШИБКА при разметке «{source_name}»:\n{exc}\n")
                return 1
            found = scan_placeholders(folder / target_name)
            print(f"  {target_name}: переменных {len(found)}")
            print("     " + ", ".join(sorted(set(found))))
            total += 1
    print("\n" + "=" * 62)
    print(f"Готово: размечено бланков — {total}. Оригиналы не изменялись.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
