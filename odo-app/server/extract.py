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
        from concurrent.futures import ThreadPoolExecutor
        env = dict(os.environ)
        # Один поток на страницу: tesseract с OpenMP при нескольких процессах или занятом процессоре
        # уходил в ожидание — страница шла 2,5 минуты вместо 4 секунд. Параллелим страницами, не потоками.
        env["OMP_THREAD_LIMIT"] = "1"
        n = len(doc)
        workers = max(1, min(4, (os.cpu_count() or 1)))
        with tempfile.TemporaryDirectory() as td:
            pngs = []
            for i, p in enumerate(doc):
                png = Path(td) / f"p{i}.png"
                p.get_pixmap(dpi=200).save(str(png))
                pngs.append(png)
            done = {"n": 0}
            if progress:
                progress(0, n, "ocr")

            def one(i_png):
                i, png = i_png
                r = subprocess.run([cmd, str(png), "-", "-l", "rus+eng", "--psm", "3"], capture_output=True, text=True, env=env,
                                   encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                done["n"] += 1
                if progress:
                    progress(done["n"], n, "ocr")
                return i, (r.stdout or "")

            with ThreadPoolExecutor(max_workers=workers) as ex:
                pages = dict(ex.map(one, enumerate(pngs)))
        text = "".join(f"\n===== стр. {i + 1} =====\n" + pages[i] for i in range(n))
        _pdf_text.last_ocr = len(text.strip()) >= 40 * n
        return text, len(text.strip()) < 40 * n
    return text, True


_pdf_text.last_ocr = False


def _rtf_text(path: Path) -> str:
    """RTF без библиотек: \\'hh — байт кодовой страницы, \\uN — юникод (после него \\ucN знаков пропускается), служебные группы выбрасываются."""
    import re as _re
    raw = path.read_bytes().decode("latin-1")
    m = _re.search(r"\\ansicpg(\d+)", raw)
    cp = "cp" + m.group(1) if m and m.group(1) not in ("0",) else "cp1251"
    out, buf = [], bytearray()
    skip_groups = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "header", "footer", "xmlnstbl", "themedata", "colorschememapping", "latentstyles", "datastore", "listtable", "listoverridetable", "rsidtbl", "generator"}
    stack, depth_skip, uc, i, n = [], None, 1, 0, len(raw)

    def flush():
        if buf:
            out.append(buf.decode(cp, errors="replace")); buf.clear()
    while i < n:
        ch = raw[i]
        if ch == "{":
            stack.append(uc); i += 1
            mm = _re.match(r"\\(?:\*\\)?([A-Za-z]+)", raw[i:i + 24])
            if depth_skip is None and mm and (mm.group(1) in skip_groups or raw[i:i + 2] == "\\*"):
                depth_skip = len(stack)
            continue
        if ch == "}":
            if stack:
                uc = stack.pop()
                if depth_skip is not None and len(stack) < depth_skip:
                    depth_skip = None
            i += 1; continue
        if ch == "\\":
            mm = _re.match(r"\\([A-Za-z]+)(-?\d+)? ?|\\'([0-9a-fA-F]{2})|\\(.)", raw[i:])
            if not mm:
                i += 1; continue
            i += mm.end()
            if depth_skip is not None:
                continue
            if mm.group(3):
                buf.append(int(mm.group(3), 16)); continue
            if mm.group(4) is not None:
                flush(); out.append({"\\": "\\", "{": "{", "}": "}", "~": " ", "-": "", "_": "-", "\n": "\n"}.get(mm.group(4), "")); continue
            word, arg = mm.group(1), mm.group(2)
            if word == "u" and arg is not None:
                flush(); code = int(arg); out.append(chr(code + 65536 if code < 0 else code)); i += uc; continue
            if word == "uc" and arg is not None:
                uc = int(arg); continue
            if word in ("par", "line", "row", "sect", "page"):
                flush(); out.append("\n"); continue
            if word in ("tab", "cell"):
                flush(); out.append(" | " if word == "cell" else "\t"); continue
            continue
        if depth_skip is None and ch not in "\r\n":
            buf.append(ord(ch) if ord(ch) < 256 else 63)
        i += 1
    flush()
    return _re.sub(r"[ \t]+\n", "\n", "".join(out))


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
    elif ext == ".rtf":
        text = _rtf_text(p)
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
