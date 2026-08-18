# -*- coding: utf-8 -*-
"""Движок подстановки переменных {{...}} в DOCX.

Почему не «простая замена текста»:
Word разбивает даже одно слово на несколько фрагментов (runs) — из-за
проверки орфографии, следов правок и т.п. Поэтому движок:

  * склеивает текст всех фрагментов абзаца в одну строку;
  * ищет {{переменные}} уже в склеенной строке;
  * возвращает значение в ПЕРВЫЙ фрагмент переменной, остальные части
    вычищает — формат (шрифт, размер, жирность) берётся у первого
    фрагмента, то есть ровно тот, что был у пропуска в шаблоне.

Файл шаблона обрабатывается на уровне ZIP: части документа, которых мы
не касались (стили, тема, шрифты, нумерация, настройки), переносятся
в результат байт в байт. Это и есть гарантия «как в шаблоне».

Обрабатываются: основной текст, таблицы (в т.ч. вложенные), колонтитулы,
сноски, надписи (текстовые поля), а также адреса гиперссылок.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")

#: Части пакета, в которых имеет смысл искать переменные.
_TEXT_PARTS = re.compile(
    r"^word/(document\d*\.xml|header\d*\.xml|footer\d*\.xml|footnotes\.xml|endnotes\.xml)$"
)
_RELS_PARTS = re.compile(r"^word/_rels/.+\.rels$")


class TemplateError(Exception):
    """Ошибка работы с шаблоном, текст рассчитан на пользователя."""


@dataclass
class FillReport:
    """Итог заполнения одного документа."""

    replaced: dict[str, int] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)   # переменные, которых нет в данных
    left_empty: list[str] = field(default_factory=list)  # переменные с пустым значением

    @property
    def total(self) -> int:
        return sum(self.replaced.values())


# --------------------------------------------------------------- обход XML
def paragraph_text(paragraph) -> str:
    """Текст абзаца так, как он выглядит: табуляции — пробелами.

    Нужно для проверок и вывода: без этого «дата\tгород» слипалось
    в «датагород» и выглядело ошибкой, хотя в документе всё верно.
    """
    parts: list[str] = []

    def walk(node) -> None:
        for child in node:
            if child.tag == W + "p":
                continue
            if child.tag == W + "t":
                parts.append(child.text or "")
            elif child.tag == W + "tab":
                parts.append("\t")
            elif child.tag == W + "br":
                parts.append("\n")
            else:
                walk(child)

    walk(paragraph)
    return "".join(parts)


def _own_text_nodes(paragraph) -> list:
    """Все w:t этого абзаца, НЕ считая вложенных абзацев (надписи, таблицы внутри)."""
    found: list = []

    def walk(node) -> None:
        for child in node:
            if child.tag == W + "p":
                continue  # вложенный абзац обработается отдельно
            if child.tag == W + "t":
                found.append(child)
            else:
                walk(child)

    walk(paragraph)
    return found


def _iter_paragraphs(root):
    return root.iter(W + "p")


def _fill_paragraph(paragraph, values: dict[str, str], report: FillReport) -> None:
    nodes = _own_text_nodes(paragraph)
    if not nodes:
        return

    texts = [node.text or "" for node in nodes]
    joined = "".join(texts)
    if "{{" not in joined:
        return

    spans: list[tuple[int, int, int]] = []
    position = 0
    for index, text in enumerate(texts):
        spans.append((index, position, position + len(text)))
        position += len(text)

    new_texts = list(texts)
    touched = False

    # Справа налево: тогда смещения слева остаются верными.
    for match in reversed(list(PLACEHOLDER_RE.finditer(joined))):
        name = match.group(1)
        if name not in values:
            if name not in report.unknown:
                report.unknown.append(name)
            continue

        value = values[name]
        value = "" if value is None else str(value)
        if not value and name not in report.left_empty:
            report.left_empty.append(name)

        start, end = match.start(), match.end()
        first = True
        for index, span_start, span_end in spans:
            if span_end <= start or span_start >= end:
                continue
            local_start = max(start, span_start) - span_start
            local_end = min(end, span_end) - span_start
            current = new_texts[index]
            if first:
                new_texts[index] = current[:local_start] + value + current[local_end:]
                first = False
            else:
                new_texts[index] = current[:local_start] + current[local_end:]
        report.replaced[name] = report.replaced.get(name, 0) + 1
        touched = True

    if not touched:
        return

    for node, old, new in zip(nodes, texts, new_texts):
        if old == new:
            continue
        node.text = new
        node.set(XML_SPACE, "preserve")


def _fill_xml(data: bytes, values: dict[str, str], report: FillReport) -> bytes | None:
    """Подставить значения в одну XML-часть. None — если ничего не менялось."""
    if b"{{" not in data:
        return None
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False)
    root = etree.fromstring(data, parser)
    before = report.total
    for paragraph in _iter_paragraphs(root):
        _fill_paragraph(paragraph, values, report)
    if report.total == before and not report.unknown:
        return None
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _fill_rels(data: bytes, values: dict[str, str], report: FillReport) -> bytes | None:
    """Адреса гиперссылок (например mailto:{{email}}) тоже могут быть шаблонными."""
    if b"{{" not in data:
        return None
    text = data.decode("utf-8")

    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in values:
            if name not in report.unknown:
                report.unknown.append(name)
            return match.group(0)
        report.replaced[name] = report.replaced.get(name, 0) + 1
        # В URL нельзя оставлять пробелы и кавычки.
        value = str(values[name] or "")
        return value.replace(" ", "%20").replace('"', "%22").replace("&", "&amp;")

    new_text = PLACEHOLDER_RE.sub(replace, text)
    if new_text == text:
        return None
    return new_text.encode("utf-8")


# --------------------------------------------------------------- публичное API
def fill_template(template_path: str | Path, output_path: str | Path,
                  values: dict[str, str]) -> FillReport:
    """Заполнить шаблон значениями и сохранить результат в новый файл.

    Исходный шаблон не изменяется никогда: он открывается только на чтение.
    """
    template_path = Path(template_path)
    output_path = Path(output_path)

    if not template_path.exists():
        raise TemplateError(f"Шаблон не найден: {template_path}")
    if template_path.resolve() == output_path.resolve():
        raise TemplateError(
            "Попытка записать результат поверх шаблона. Операция отменена."
        )

    report = FillReport()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(template_path, "r") as source:
            if source.testzip() is not None:
                raise TemplateError(f"Файл шаблона повреждён: {template_path.name}")
            names = source.namelist()
            if "word/document.xml" not in names:
                raise TemplateError(
                    f"Файл «{template_path.name}» не похож на документ Word (.docx)."
                )
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target:
                for item in source.infolist():
                    data = source.read(item.filename)
                    new_data = None
                    if _TEXT_PARTS.match(item.filename):
                        new_data = _fill_xml(data, values, report)
                    elif _RELS_PARTS.match(item.filename):
                        new_data = _fill_rels(data, values, report)
                    target.writestr(item, new_data if new_data is not None else data)
    except zipfile.BadZipFile as exc:
        temp_path.unlink(missing_ok=True)
        raise TemplateError(
            f"Файл «{template_path.name}» повреждён или не является документом Word."
        ) from exc
    except TemplateError:
        temp_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        raise TemplateError(
            f"Не удалось заполнить шаблон «{template_path.name}». "
            f"Техническая причина: {exc}"
        ) from exc

    shutil.move(str(temp_path), str(output_path))
    return report


def scan_placeholders(template_path: str | Path) -> list[str]:
    """Список переменных, встречающихся в шаблоне (в порядке появления)."""
    template_path = Path(template_path)
    found: list[str] = []
    try:
        with zipfile.ZipFile(template_path, "r") as source:
            for item in source.infolist():
                if not (_TEXT_PARTS.match(item.filename) or _RELS_PARTS.match(item.filename)):
                    continue
                data = source.read(item.filename)
                if b"{{" not in data:
                    continue
                if _RELS_PARTS.match(item.filename):
                    text = data.decode("utf-8")
                    for match in PLACEHOLDER_RE.finditer(text):
                        if match.group(1) not in found:
                            found.append(match.group(1))
                    continue
                root = etree.fromstring(data)
                for paragraph in _iter_paragraphs(root):
                    joined = "".join(n.text or "" for n in _own_text_nodes(paragraph))
                    for match in PLACEHOLDER_RE.finditer(joined):
                        if match.group(1) not in found:
                            found.append(match.group(1))
    except zipfile.BadZipFile as exc:
        raise TemplateError(
            f"Файл «{template_path.name}» повреждён или не является документом Word."
        ) from exc
    return found


def extract_all_text(docx_path: str | Path) -> str:
    """Весь текст документа — для контроля качества готового файла."""
    docx_path = Path(docx_path)
    chunks: list[str] = []
    try:
        with zipfile.ZipFile(docx_path, "r") as source:
            for item in source.infolist():
                if not _TEXT_PARTS.match(item.filename):
                    continue
                root = etree.fromstring(source.read(item.filename))
                for paragraph in _iter_paragraphs(root):
                    line = paragraph_text(paragraph)
                    if line.strip():
                        chunks.append(line)
    except zipfile.BadZipFile as exc:
        raise TemplateError(
            f"Готовый файл «{docx_path.name}» не открывается как документ Word."
        ) from exc
    return "\n".join(chunks)


def extract_package_text(docx_path: str | Path) -> str:
    """Текст всех текстовых частей и связей — для поиска чужих реквизитов."""
    docx_path = Path(docx_path)
    chunks: list[str] = []
    with zipfile.ZipFile(docx_path, "r") as source:
        for item in source.infolist():
            if _TEXT_PARTS.match(item.filename) or _RELS_PARTS.match(item.filename):
                chunks.append(source.read(item.filename).decode("utf-8", "ignore"))
    return "\n".join(chunks)
