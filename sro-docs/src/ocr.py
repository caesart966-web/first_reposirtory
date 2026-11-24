# -*- coding: utf-8 -*-
"""Распознавание карточки со скана.

Карточку предприятия часто присылают сканом: внутри PDF лежит картинка,
текста в нём нет вовсе. Обычное чтение в таком файле не находит ни строки.

Просто «прогнать через распознавание» мало. Карточка — это таблица из двух
колонок: слева подпись поля, справа значение. Распознавание отдаёт текст
строками во всю ширину, и подпись склеивается со значением: «Юридический
адрес (с почтовым 191023, г. Санкт-Петербург…». Разобрать такое нельзя.

Поэтому берём у распознавания КООРДИНАТЫ каждого слова, собираем слова
в строки, находим границу между колонками и возвращаем пары
«подпись — значение» — ровно в том виде, в каком читаются таблицы Word.

ВАЖНО: распознанные цифры нельзя считать достоверными. На одном и том же
скане БИК при разном разрешении читался то «…790», то «…750». Контрольные
числа ИНН и ОГРН такую подмену ловят, а у БИК, счетов и ОКПО проверки нет,
поэтому результат помечается как снятый со скана и требует сверки глазами.
"""
from __future__ import annotations

import io
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


class OcrUnavailable(Exception):
    """Распознавание не настроено: нет библиотек или самой программы."""


@dataclass
class Recognized:
    text: str = ""
    pairs: list[tuple[str, str]] = field(default_factory=list)


#: Разрешение отрисовки. 400 точек на дюйм — разумная середина: на 300
#: мелкие цифры путаются, на 600 распознавание втрое дольше без заметной
#: пользы на обычных сканах.
DPI = 400

#: Просвет между колонками считается значимым, если шире этой доли страницы.
_GAP_SHARE = 0.04

#: Строка продолжает предыдущую, а не начинает новое поле: начинается
#: со строчной буквы («индексом)» под «Юридический адрес (с почтовым»).
_CONTINUATION_RE = re.compile(r"^[а-яё\d)]", re.IGNORECASE | re.UNICODE)
_LOWER_START_RE = re.compile(r"^[а-яё)]")


def _require(module: str, human: str):
    try:
        return __import__(module)
    except ImportError as exc:
        raise OcrUnavailable(
            f"Для чтения сканов нужна библиотека {human}."
        ) from exc


def page_images(path: Path) -> list:
    """Страницы PDF как картинки. Для файла-картинки — она сама."""
    Image = _require("PIL.Image", "pillow").Image
    if path.suffix.lower() != ".pdf":
        return [Image.open(str(path))]

    pymupdf = _require("pymupdf", "pymupdf")
    document = pymupdf.open(str(path))
    try:
        return [Image.open(io.BytesIO(
            page.get_pixmap(dpi=DPI).tobytes("png"))) for page in document]
    finally:
        document.close()


#: Куда установщик Tesseract кладёт программу на Windows. Галочку «добавить
#: в PATH» при установке часто не ставят, и тогда программа есть, а найти её
#: нельзя. Поэтому смотрим ещё и в обычные места.
_WINDOWS_PLACES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def find_tesseract() -> str | None:
    """Путь к программе Tesseract или None, если её нет."""
    import os
    import shutil

    found = shutil.which("tesseract")
    if found:
        return found
    places = list(_WINDOWS_PLACES)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        places.append(str(Path(local) / "Programs" / "Tesseract-OCR"
                          / "tesseract.exe"))
    for place in places:
        if Path(place).exists():
            return place
    return None


def _words(image) -> list[dict]:
    """Слова страницы с координатами."""
    pytesseract = _require("pytesseract", "pytesseract")
    where = find_tesseract()
    if where is None:
        raise OcrUnavailable(
            "Программа Tesseract OCR не найдена на этом компьютере.")
    pytesseract.pytesseract.tesseract_cmd = where
    try:
        data = pytesseract.image_to_data(
            image, lang="rus+eng", output_type=pytesseract.Output.DICT)
    except Exception as exc:          # сама программа Tesseract не найдена
        raise OcrUnavailable(str(exc)) from exc
    return [{"text": text.strip(), "left": data["left"][index],
             "top": data["top"][index], "width": data["width"][index],
             "height": data["height"][index]}
            for index, text in enumerate(data["text"]) if text.strip()]


def _rows(words: list[dict]) -> list[list[dict]]:
    """Слова → строки. Слово начинает новую строку, если ушло ниже предыдущей."""
    words = sorted(words, key=lambda w: (w["top"], w["left"]))
    rows, current = [], []
    for word in words:
        if current and word["top"] > current[-1]["top"] + current[-1]["height"] * 0.6:
            rows.append(sorted(current, key=lambda w: w["left"]))
            current = []
        current.append(word)
    if current:
        rows.append(sorted(current, key=lambda w: w["left"]))
    return rows


def _column_edge(rows: list[list[dict]], width: int) -> float | None:
    """Граница колонок — там, где чаще всего начинается правая колонка.

    Границу ищем одну на всю страницу, а не в каждой строке: тогда строки
    переноса, где подпись пустая, попадают в правильную колонку.
    """
    bucket = max(width // 40, 1)
    votes: Counter = Counter()
    starts: dict[int, list[int]] = {}
    for row in rows:
        for left, right in zip(row, row[1:]):
            gap = right["left"] - (left["left"] + left["width"])
            if gap > width * _GAP_SHARE:
                index = right["left"] // bucket
                votes[index] += 1
                starts.setdefault(index, []).append(right["left"])
    if not votes:
        return None
    # Граница — САМОЕ ЛЕВОЕ слово победившей корзины, а не её середина.
    # По середине граница вставала правее некоторых значений, и те уезжали
    # в колонку подписей — поле теряло значение целиком.
    return float(min(starts[votes.most_common(1)[0][0]]))


def _pairs_from_rows(rows: list[list[dict]], edge: float) -> tuple[list, list]:
    """Строки → пары «подпись — значение» и остальной текст."""
    pairs: list[list[str]] = []
    loose: list[str] = []
    for row in rows:
        label = " ".join(w["text"] for w in row if w["left"] < edge).strip()
        value = " ".join(w["text"] for w in row if w["left"] >= edge).strip()
        if not label and not value:
            continue
        if not label:
            # Подписи нет — это перенос значения предыдущей строки.
            if pairs:
                pairs[-1][1] = (pairs[-1][1] + " " + value).strip()
            else:
                loose.append(value)
            continue
        if pairs and _LOWER_START_RE.match(label):
            # Подпись перенесена на вторую строку: «индексом)».
            pairs[-1][0] = (pairs[-1][0] + " " + label).strip()
            pairs[-1][1] = (pairs[-1][1] + " " + value).strip()
            continue
        if not value:
            loose.append(label)
            continue
        pairs.append([label, value])
    return [(a, b) for a, b in pairs], loose


def recognize(path: Path) -> Recognized:
    """Распознать карточку: пары «подпись — значение» плюс прочий текст."""
    pairs: list[tuple[str, str]] = []
    lines: list[str] = []
    for image in page_images(path):
        words = _words(image)
        if not words:
            continue
        rows = _rows(words)
        edge = _column_edge(rows, image.width)
        if edge is None:
            lines += [" ".join(w["text"] for w in row) for row in rows]
            continue
        found, loose = _pairs_from_rows(rows, edge)
        pairs += found
        lines += loose
    return Recognized("\n".join(lines), pairs)
