#!/usr/bin/env python3
"""Выгрузка реестра членов СРО с reestr.nostroy.ru в XLSX/CSV.

Тот же API, что и у браузерного скрипта nostroy-export.js, но без браузера.
Зависимостей нет — только стандартная библиотека.

    python3 nostroy_export.py --sro 410
    python3 nostroy_export.py --sro 410 --cookie "$(скопировать Cookie из DevTools)"

Если API откажет без браузерной сессии (401/403/419), передай --cookie
со значением заголовка Cookie из вкладки Network или используй nostroy-export.js.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any

DEFAULT_BASE = "https://reestr.nostroy.ru"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# --------------------------------------------------------------- разбор ответа


def pick_items(payload: Any) -> list[dict]:
    """Находит в ответе массив записей независимо от имени ключа."""
    best: list | None = None

    def walk(node: Any, depth: int) -> None:
        nonlocal best
        if depth > 5 or not isinstance(node, (dict, list)):
            return
        if isinstance(node, list):
            objects = [x for x in node if isinstance(x, dict)]
            if objects and (best is None or len(objects) > len(best)):
                best = node
            return
        for value in node.values():
            walk(value, depth + 1)

    walk(payload, 0)
    return [x for x in (best or []) if isinstance(x, dict)]


def pick_meta(payload: Any) -> dict[str, int | None]:
    """Достаёт countPages/count независимо от их имён в ответе."""
    meta: dict[str, int | None] = {"countPages": None, "count": None}

    def as_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    def walk(node: Any, depth: int) -> None:
        if depth > 5 or not isinstance(node, dict):
            return
        for key, value in node.items():
            number = as_int(value)
            if number is not None:
                if meta["countPages"] is None and re.fullmatch(
                    r"countpages|pagescount|pages|totalpages|last_?page", key, re.I
                ):
                    meta["countPages"] = number
                if meta["count"] is None and re.fullmatch(
                    r"count|total|totalcount|totalitems|records", key, re.I
                ):
                    meta["count"] = number
            walk(value, depth + 1)

    walk(payload, 0)
    return meta


# ------------------------------------------------------------------- запросы


class Api:
    def __init__(self, base: str, sro_id: int, cookie: str | None, retries: int, delay: float):
        self.url = f"{base.rstrip('/')}/api/sro/{sro_id}/member/list"
        self.cookie = cookie
        self.retries = retries
        self.delay = delay

    def fetch_page(self, page: int, page_count: int) -> dict:
        body = json.dumps(
            {"filters": {}, "page": page, "pageCount": str(page_count), "sortBy": {}}
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": UA,
            "Origin": self.url.split("/api/")[0],
            "Referer": self.url.split("/api/")[0] + "/",
        }
        if self.cookie:
            headers["Cookie"] = self.cookie

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            if attempt:
                time.sleep(min(8.0, 0.5 * 2 ** (attempt - 1)))
            try:
                request = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(request, timeout=60) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if self.delay:
                    time.sleep(self.delay)
                return payload
            except urllib.error.HTTPError as error:
                if error.code in (401, 403, 419):
                    raise SystemExit(
                        f"HTTP {error.code}: API требует сессию браузера. "
                        "Передай --cookie со значением заголовка Cookie из DevTools "
                        "или запусти nostroy-export.js в консоли Chrome."
                    ) from error
                last_error = error
                if error.code not in (429,) and error.code < 500:
                    raise
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                last_error = error
        raise RuntimeError(f"страница {page} не загрузилась: {last_error}")


def probe_page_count(api: Api) -> tuple[int, dict | None]:
    """Подбирает максимальный pageCount, который сервер реально отдаёт."""
    fallback = 20
    for want in (500, 100, 50, 20):
        payload = api.fetch_page(1, want)
        got = len(pick_items(payload))
        total = pick_meta(payload)["count"]
        if got >= want or (total is not None and got >= total):
            print(f"[СРО] сервер отдаёт по {got} записей на страницу — pageCount={want}")
            return want, payload
        print(f"[СРО] pageCount={want} урезан до {got}, пробуем меньше")
        fallback = max(fallback, got)
    return fallback, None


def fetch_all(api: Api, page_count: int | None, concurrency: int, max_pages: int) -> list[dict]:
    if page_count:
        first = api.fetch_page(1, page_count)
    else:
        page_count, first = probe_page_count(api)
        if first is None:
            first = api.fetch_page(1, page_count)

    first_items = pick_items(first)
    if not first_items:
        raise SystemExit("API вернул пустой список — проверь --sro.")

    meta = pick_meta(first)
    total_pages = meta["countPages"]
    if total_pages is None and meta["count"] is not None:
        total_pages = -(-meta["count"] // page_count)
    total_pages = min(total_pages or max_pages, max_pages)
    print(f"[СРО] всего записей: {meta['count']}, страниц: {total_pages}")

    pages: dict[int, list[dict]] = {1: first_items}
    failed: list[int] = []

    def load(page: int) -> None:
        try:
            pages[page] = pick_items(api.fetch_page(page, page_count))
        except Exception as error:  # noqa: BLE001 — страницу добираем повторным запуском
            print(f"[СРО] страница {page}: {error}", file=sys.stderr)
            failed.append(page)
            pages[page] = []

    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            for done, _ in enumerate(pool.map(load, range(2, total_pages + 1)), start=2):
                if done % 10 == 0 or done == total_pages:
                    print(f"[СРО] страниц загружено {done}/{total_pages}")

    rows: list[dict] = []
    seen: set[str] = set()
    for page in sorted(pages):
        for row in pages[page]:
            key = f"id:{row['id']}" if "id" in row else json.dumps(row, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    if failed:
        print(f"[СРО] не загружены страницы: {sorted(failed)} — запусти скрипт ещё раз", file=sys.stderr)
    if meta["count"] is not None and len(rows) != meta["count"]:
        print(f"[СРО] собрано {len(rows)} из {meta['count']} записей", file=sys.stderr)
    return rows


# ------------------------------------------------------------ плоская таблица

RU_HEADERS = {
    "id": "ID", "name": "Наименование", "fullname": "Полное наименование",
    "full_name": "Полное наименование", "shortname": "Краткое наименование",
    "short_name": "Краткое наименование", "inn": "ИНН", "kpp": "КПП",
    "ogrn": "ОГРН/ОГРНИП", "ogrnip": "ОГРН/ОГРНИП", "okpo": "ОКПО",
    "number": "Регистрационный номер", "registration_number": "Регистрационный номер",
    "registrationnumber": "Регистрационный номер", "reg_number": "Регистрационный номер",
    "regnumber": "Регистрационный номер", "status": "Статус", "statusname": "Статус",
    "status_name": "Статус", "registration_date": "Дата регистрации",
    "registrationdate": "Дата регистрации", "date_registration": "Дата регистрации",
    "exclusion_date": "Дата исключения", "exclusiondate": "Дата исключения",
    "address": "Адрес", "legal_address": "Юридический адрес", "phone": "Телефон",
    "email": "E-mail", "site": "Сайт", "website": "Сайт", "director": "Руководитель",
    "head": "Руководитель", "chief": "Руководитель", "sro": "СРО", "sro_name": "СРО",
    "region": "Регион",
}

RU_PATTERNS = [
    (re.compile(r"(compensation|comp|kf).*(vv|vozmeshhen|vozmesch)", re.I), "КФ ВВ (взнос)"),
    (re.compile(r"(compensation|comp|kf).*(odo|obespechen)", re.I), "КФ ОДО (взнос)"),
    (re.compile(r"level.*(vv|responsib|otvet)", re.I), "Уровень ответственности ВВ"),
    (re.compile(r"level.*(odo|dogovor)", re.I), "Уровень ответственности ОДО"),
    (re.compile(r"vv.*level", re.I), "Уровень ответственности ВВ"),
    (re.compile(r"odo.*level", re.I), "Уровень ответственности ОДО"),
    (re.compile(r"(right|pravo).*(osobo|opasn|technical)", re.I), "Право на особо опасные объекты"),
    (re.compile(r"(right|pravo).*(atom|nuclear)", re.I), "Право на объекты атомной энергии"),
    (re.compile(r"basis|osnovanie", re.I), "Основание"),
    (re.compile(r"note|comment|primech", re.I), "Примечание"),
]

PRIORITY = [
    re.compile(r"^(name|full_?name|short_?name)$", re.I),
    re.compile(r"reg.*num|^number$", re.I),
    re.compile(r"^inn$", re.I),
    re.compile(r"ogrn", re.I),
    re.compile(r"status", re.I),
    re.compile(r"registration_?date|date.*registr", re.I),
    re.compile(r"exclusion|iskl", re.I),
]

FORCE_TEXT = re.compile(r"inn|ogrn|kpp|okpo|snils|phone|тел|bik|schet|account", re.I)


def flatten(obj: dict, out: dict | None = None, prefix: str = "", depth: int = 0) -> dict:
    out = {} if out is None else out
    if depth > 4:
        return out
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        if value is None:
            out[path] = ""
        elif isinstance(value, bool):
            out[path] = "да" if value else "нет"
        elif isinstance(value, list):
            if all(not isinstance(x, (dict, list)) for x in value):
                out[path] = "; ".join("" if x is None else str(x) for x in value)
            elif len(value) == 1 and isinstance(value[0], dict):
                flatten(value[0], out, path, depth + 1)
            else:
                out[path] = " | ".join(
                    str(x.get("name") or x.get("title") or json.dumps(x, ensure_ascii=False))
                    if isinstance(x, dict) else str(x)
                    for x in value
                )
        elif isinstance(value, dict):
            flatten(value, out, path, depth + 1)
        else:
            out[path] = value
    return out


def human_header(path: str, mode: str) -> str:
    if mode == "raw":
        return path
    normalized = re.sub(r"[_.]", "", path)
    for pattern, label in RU_PATTERNS:
        if pattern.search(path) or pattern.search(normalized):
            return label
    return " → ".join(RU_HEADERS.get(segment.lower(), segment) for segment in path.split("."))


def build_table(rows: list[dict], header_mode: str) -> tuple[list[str], list[str], list[list]]:
    flat = [flatten(row) for row in rows]

    columns: list[str] = []
    seen: set[str] = set()
    for row in flat:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)

    head: list[str] = []
    for pattern in PRIORITY:
        for column in columns:
            if "." not in column and column not in head and pattern.search(column):
                head.append(column)
    if not head:
        for pattern in PRIORITY:
            for column in columns:
                if column not in head and pattern.search(column.split(".")[-1]):
                    head.append(column)
    columns = head + [c for c in columns if c not in head]

    headers: list[str] = []
    used: set[str] = set()
    for column in columns:
        header = human_header(column, header_mode)
        if header in used:
            header = f"{header} ({column})"
        used.add(header)
        headers.append(header)

    data = [[row.get(column, "") for column in columns] for row in flat]
    return columns, headers, data


# ------------------------------------------------------------------- запись


def write_csv(path: str, headers: list[str], data: list[list]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(data)


def col_letter(index: int) -> str:
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def xml_escape(value: Any) -> str:
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", str(value))
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_xlsx(path: str, columns: list[str], headers: list[str], data: list[list], sheet: str) -> None:
    n_cols = len(headers)
    widths = [len(str(h)) + 2 for h in headers]
    rows_xml = [
        "<row r=\"1\">"
        + "".join(
            f'<c r="{col_letter(i + 1)}1" t="inlineStr" s="1"><is>'
            f'<t xml:space="preserve">{xml_escape(h)}</t></is></c>'
            for i, h in enumerate(headers)
        )
        + "</row>"
    ]

    for row_index, row in enumerate(data, start=2):
        cells = []
        for col_index, value in enumerate(row):
            if value == "" or value is None:
                continue
            widths[col_index] = min(60, max(widths[col_index], len(str(value)) + 2))
            ref = f"{col_letter(col_index + 1)}{row_index}"
            numeric = isinstance(value, (int, float)) and not isinstance(value, bool) \
                and not FORCE_TEXT.search(columns[col_index])
            if numeric:
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(
                    f'<c r="{ref}" t="inlineStr"><is>'
                    f'<t xml:space="preserve">{xml_escape(value)}</t></is></c>'
                )
        rows_xml.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")

    dim = f"A1:{col_letter(n_cols)}{len(data) + 1}"
    cols_xml = "".join(
        f'<col min="{i + 1}" max="{i + 1}" width="{max(8, w)}" customWidth="1"/>'
        for i, w in enumerate(widths)
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="{dim}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        "</sheetView></sheetViews>"
        '<sheetFormatPr defaultRowHeight="15"/>'
        f"<cols>{cols_xml}</cols>"
        f"<sheetData>{''.join(rows_xml)}</sheetData>"
        f'<autoFilter ref="{dim}"/>'
        "</worksheet>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{xml_escape(sheet[:31])}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        "<font><b/><sz val=\"11\"/><name val=\"Calibri\"/></font></fonts>"
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        archive.writestr("xl/styles.xml", styles)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


# --------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Выгрузка реестра членов СРО (reestr.nostroy.ru)")
    parser.add_argument("--sro", type=int, default=410, help="ID СРО в реестре (по умолчанию 410)")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--cookie", default=None, help="заголовок Cookie из DevTools, если API требует сессию")
    parser.add_argument("--page-count", type=int, default=None, help="записей на страницу (по умолчанию подбирается)")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.12, help="пауза между запросами, с")
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--max-pages", type=int, default=5000)
    parser.add_argument("--headers", choices=("ru", "raw"), default="ru")
    parser.add_argument("--format", default="xlsx,csv", help="xlsx, csv или xlsx,csv")
    parser.add_argument("--out", default=None, help="префикс имени файлов")
    args = parser.parse_args(argv)

    api = Api(args.base_url, args.sro, args.cookie, args.retries, args.delay)
    started = time.time()
    rows = fetch_all(api, args.page_count, args.concurrency, args.max_pages)
    columns, headers, data = build_table(rows, args.headers)

    prefix = args.out or f"reestr_nostroy_sro_{args.sro}_{date.today().isoformat()}"
    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    if "csv" in formats:
        write_csv(f"{prefix}.csv", headers, data)
        print(f"[СРО] сохранено: {prefix}.csv")
    if "xlsx" in formats:
        write_xlsx(f"{prefix}.xlsx", columns, headers, data, f"СРО {args.sro}")
        print(f"[СРО] сохранено: {prefix}.xlsx")

    print(f"[СРО] готово: {len(data)} записей, {len(headers)} колонок, за {time.time() - started:.0f} c")
    print("[СРО] колонки: " + " | ".join(headers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
