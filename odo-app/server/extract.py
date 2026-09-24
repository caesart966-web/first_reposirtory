"""Текст из документов: DOCX (XML напрямую), PDF (pymupdf, при отсутствии слоя — tesseract, если стоит), XLSX, TXT."""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        x = z.read("word/document.xml").decode("utf-8", errors="replace")
    x = re.sub(r"<w:tab/>", "\t", x)
    x = re.sub(r"</w:p>", "\n", x)
    x = re.sub(r"</w:tc>", " | ", x)
    x = re.sub(r"</w:tr>", "\n", x)
    t = html.unescape(re.sub(r"<[^>]+>", "", x))
    return re.sub(r"\n{3,}", "\n\n", t)


def tesseract_cmd() -> str | None:
    """Путь к tesseract: из переменной ODO_TESSERACT (так его подставляет запускатор .exe) или из PATH."""
    import os
    cand = os.environ.get("ODO_TESSERACT")
    if cand and Path(cand).exists():
        return cand
    return shutil.which("tesseract")


def ocr_available() -> bool:
    return tesseract_cmd() is not None


def _pdf_text(path: Path, progress=None) -> tuple[str, bool]:
    import pymupdf
    doc = pymupdf.open(path)
    parts = []
    for i, p in enumerate(doc):
        parts.append(f"\n===== стр. {i + 1} =====\n" + p.get_text())
    text = "".join(parts)
    _pdf_text.last_ocr = False
    if len(text.strip()) > 40 * len(doc):
        if progress:
            progress(len(doc), len(doc), "text")
        return text, False
    # скан: распознаём, если есть tesseract (в .exe он встроен)
    cmd = tesseract_cmd()
    if cmd:
        import os
        env = dict(os.environ)
        out = []
        with tempfile.TemporaryDirectory() as td:
            for i, p in enumerate(doc):
                if progress:
                    progress(i, len(doc), "ocr")
                png = Path(td) / f"p{i}.png"
                p.get_pixmap(dpi=200).save(str(png))
                r = subprocess.run([cmd, str(png), "-", "-l", "rus+eng", "--psm", "3"], capture_output=True, text=True, env=env,
                                   encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                out.append(f"\n===== стр. {i + 1} =====\n" + (r.stdout or ""))
        text = "".join(out)
        if progress:
            progress(len(doc), len(doc), "ocr")
        _pdf_text.last_ocr = len(text.strip()) >= 40 * len(doc)
        return text, len(text.strip()) < 40 * len(doc)
    return text, True


_pdf_text.last_ocr = False


def _xlsx_text(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"\n===== лист {ws.title} =====")
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None and str(c).strip()]
            if cells:
                out.append(" | ".join(cells))
    return "\n".join(out)


def extract_text(path: str | Path, progress=None) -> tuple[str, dict]:
    """→ (текст, {scanned: bool, ocr: bool, kind_hint: str}). progress(page, pages, stage) — ход распознавания."""
    p = Path(path)
    ext = p.suffix.lower()
    scanned = False
    ocr = False
    if ext == ".docx":
        text = _docx_text(p)
    elif ext == ".pdf":
        text, scanned = _pdf_text(p, progress)
        ocr = _pdf_text.last_ocr
    elif ext in (".xlsx", ".xlsm"):
        text = _xlsx_text(p)
    elif ext in (".txt", ".md", ".csv"):
        text = p.read_text(encoding="utf-8", errors="replace")
    elif ext == ".doc":
        text, scanned = "", True  # старый формат: без конвертера не читается
    else:
        text = ""
    return text, {"scanned": scanned, "ocr": ocr, "kind_hint": guess_kind(p.name, text)}


def guess_kind(filename: str, text: str) -> str:
    head = (text or "")[:3000].lower()
    first = head[:600]
    name = filename.lower()
    if re.search(r"дополнительн\w+\s+соглашени", first):
        return "addendum"
    if re.search(r"акт\w*\s+о\s+приемк\w+\s+выполненных\s+работ|\bкс-2\b|\bкс-3\b|унифицированная форма № кс|справк\w+\s+о\s+стоимости\s+выполненных", head):
        return "act"
    if re.search(r"^\s*(?:государственный\s+|муниципальный\s+)?(?:контракт|договор)\b", first) or re.search(r"(?:контракт|договор)\s*№", first[:300]):
        return "contract"
    if re.search(r"(?:объектн|сводн|локальн)\w*\s+сметн\w*\s+расч[её]т|локальн\w+\s+смет\w+|ведомост\w+\s+объ[её]мов\s+работ|сметн\w+\s+стоимость", head):
        return "estimate"
    if re.search(r"возражени|не согласн|просим исключить|уважаем", head[:1500]):
        return "letter"
    if "смет" in name:
        return "estimate"
    if "контракт" in name or "договор" in name:
        return "contract"
    return "other"
