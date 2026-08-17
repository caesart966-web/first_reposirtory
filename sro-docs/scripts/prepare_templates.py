# -*- coding: utf-8 -*-
"""Разметка исходных шаблонов: пропуски «_____» → переменные {{...}}.

Запускается ОДИН раз (и повторно, если СРО пришлёт новую редакцию бланка):

    python scripts/prepare_templates.py

Что делает:
  * читает нетронутые оригиналы из templates/_originals/;
  * заменяет текст СТРОГО указанных фрагментов (номер абзаца + номер
    фрагмента + ожидаемый текст) на переменные;
  * пишет результат в templates/.

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


def op_rel(old_target: str, new_target: str) -> dict:
    """Заменить адрес гиперссылки в word/_rels/document.xml.rels."""
    return {"kind": "rel", "expected": old_target, "new": new_target}


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
    op_cell(4, 1, 1, "V", "{{mark_object_ordinary}}"),
    op_cell(4, 2, 1, "", "{{mark_object_hazardous}}"),
    op_cell(4, 3, 1, "", "{{mark_object_nuclear}}"),

    # --- п.8 уровень ответственности, КФ возмещения вреда (таблица №5) ---
    op_cell(5, 1, 3, "v", "{{mark_harm_level1}}"),
    op_cell(5, 2, 3, "", "{{mark_harm_level2}}"),
    op_cell(5, 3, 3, "", "{{mark_harm_level3}}"),
    op_cell(5, 4, 3, "", "{{mark_harm_level4}}"),
    op_cell(5, 5, 3, "", "{{mark_harm_level5}}"),

    # --- п.9 уровень ответственности, КФ обеспечения дог. обязательств (таблица №6) ---
    op_cell(6, 1, 3, "", "{{mark_contract_level1}}"),
    op_cell(6, 2, 3, "", "{{mark_contract_level2}}"),
    op_cell(6, 3, 3, "", "{{mark_contract_level3}}"),
    op_cell(6, 4, 3, "", "{{mark_contract_level4}}"),
    op_cell(6, 5, 3, "", "{{mark_contract_level5}}"),

    # --- подпись ---
    op_text(125, 0, "Генеральный директор ", "{{director_position}} "),
    op_text(125, 1, "ООО ", "{{legal_form_short}} "),
    op_text(125, 3, "_____________   ", "{{short_name_bare}}"),
    op_text(125, 9, "___________________", "{{director_short_name}}"),
    op_text(125, 10, ".", ""),

    # --- чужая почта, оставшаяся в гиперссылке от прошлой компании ---
    op_rel("mailto:regionrem@mail.ru", "mailto:{{email}}"),
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

TEMPLATES = [
    ("Заявление_о_вступлении_ОРИГИНАЛ.docx", "01_Заявление_о_вступлении.docx", APPLICATION_OPS),
    ("Доверенность_ОРИГИНАЛ.docx", "02_Доверенность.docx", POWER_OPS),
]


# ============================================================ реализация
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


def apply_ops(document_xml: bytes, ops: list[dict], label: str) -> bytes:
    root = etree.fromstring(document_xml)
    paragraphs = list(_iter_paragraphs(root))
    tables = list(root.iter(W + "tbl"))

    for op in ops:
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


def main() -> int:
    originals = ROOT / "templates" / "_originals"
    output = ROOT / "templates"

    print("Разметка шаблонов")
    print("=" * 60)
    for source_name, target_name, ops in TEMPLATES:
        source = originals / source_name
        target = output / target_name
        if not source.exists():
            print(f"  ПРОПУЩЕН: не найден оригинал {source}")
            continue
        try:
            prepare(source, target, ops)
        except PrepareError as exc:
            print(f"\nОШИБКА при разметке «{source_name}»:\n{exc}\n")
            return 1
        from src.docx_engine import scan_placeholders
        found = scan_placeholders(target)
        print(f"  {source_name}")
        print(f"    → {target_name}: переменных {len(found)}")
        for name in found:
            print(f"        {{{{{name}}}}}")
    print("=" * 60)
    print("Готово. Оригиналы не изменялись.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
