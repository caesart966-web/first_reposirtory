"""Реестр МСП ФНС — базовый список юрлиц с ОКВЭД и регионом.

Открытые данные: https://www.nalog.gov.ru/opendata/7707329152-rsmp/
Выгрузка — ZIP-архив с множеством XML-файлов (обновляется ежемесячно,
размер ~1.5–2 ГБ). Парсим потоково через iterparse, в память архив
целиком не загружаем.

Ограничение источника: реестр содержит только субъекты малого и среднего
предпринимательства. Крупные компании добавляйте командой `import-inn`
(списком ИНН) — остальные поля дотянет обогащение из ЕГРЮЛ.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import IO, Iterator

import requests

from ..config import RSMP_META_URL, RSMP_PASSPORT_URL

_ZIP_URL_RE = re.compile(r"https?://[^\s\"';,<>]+\.zip")
_DATE_IN_NAME_RE = re.compile(r"data-(\d{2})(\d{2})(\d{4})")

_MSP_CATEGORIES = {"1": "микро", "2": "малое", "3": "среднее"}


def _local(tag: str) -> str:
    """Имя тега без namespace."""
    return tag.rsplit("}", 1)[-1]


def _iso_date(raw: str) -> str | None:
    """ДД.ММ.ГГГГ → ГГГГ-ММ-ДД (для сортировки строкой)."""
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})$", (raw or "").strip())
    if not m:
        return None
    day, month, year = m.groups()
    return f"{year}-{month}-{day}"


def resolve_data_url(session: requests.Session) -> str:
    """Находит ссылку на актуальный ZIP выгрузки в meta.csv (или на странице паспорта)."""
    urls: list[str] = []
    for source_url in (RSMP_META_URL, RSMP_PASSPORT_URL):
        try:
            resp = session.get(source_url, timeout=60)
            resp.raise_for_status()
        except requests.RequestException:
            continue
        urls = _ZIP_URL_RE.findall(resp.content.decode("utf-8", "ignore"))
        if urls:
            break
    if not urls:
        raise RuntimeError(
            "Не удалось найти ссылку на выгрузку реестра МСП. "
            "Скачайте архив вручную со страницы "
            f"{RSMP_PASSPORT_URL} и передайте путь через --rsmp-file."
        )

    def sort_key(url: str) -> tuple:
        m = _DATE_IN_NAME_RE.search(url)
        if m:
            day, month, year = m.groups()
            return (1, year, month, day)
        return (0, url)

    return max(urls, key=sort_key)


def download(url: str, dest: Path, session: requests.Session, force: bool = False) -> Path:
    """Скачивает выгрузку потоково; при обрыве связи докачивает с места остановки.

    Недокачанный файл живёт рядом как <имя>.part и переиспользуется между
    запусками, так что повторный fetch-rsmp продолжает, а не начинает заново.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"[rsmp] файл уже скачан: {dest} ({dest.stat().st_size // 2**20} МБ), пропускаю")
        return dest
    print(f"[rsmp] скачиваю {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        offset = tmp.stat().st_size if tmp.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with session.get(url, stream=True, timeout=120, headers=headers) as resp:
                if offset and resp.status_code != 206:
                    # сервер не поддержал докачку — начинаем с нуля
                    offset = 0
                resp.raise_for_status()
                mode = "ab" if offset else "wb"
                if offset:
                    print(f"[rsmp] докачиваю с {offset // 2**20} МБ")
                downloaded = offset
                with open(tmp, mode) as fh:
                    for chunk in resp.iter_content(chunk_size=2**20):
                        fh.write(chunk)
                        downloaded += len(chunk)
                        if downloaded % (200 * 2**20) < 2**20:
                            print(f"[rsmp] ...{downloaded // 2**20} МБ")
            break
        except requests.RequestException as exc:
            if attempt >= max_attempts:
                raise
            got = tmp.stat().st_size // 2**20 if tmp.exists() else 0
            print(f"[rsmp] обрыв соединения на {got} МБ ({type(exc).__name__}); "
                  f"продолжаю через 10 сек (попытка {attempt}/{max_attempts})")
            time.sleep(10)
    tmp.rename(dest)
    print(f"[rsmp] готово: {dest} ({dest.stat().st_size // 2**20} МБ)")
    return dest


def okved_matches(code: str, prefixes: tuple[str, ...]) -> bool:
    """Код подходит, если начинается с одного из префиксов (строково: "41" → "41.20")."""
    code = (code or "").strip()
    return bool(code) and any(code.startswith(p) for p in prefixes)


def _parse_document(elem: ET.Element) -> dict | None:
    """Разбирает один <Документ> реестра МСП в словарь (или None для пустого)."""
    doc: dict = {
        "kind": None,
        "inn": None,
        "ogrn": None,
        "name": None,
        "name_short": None,
        "region_code": None,
        "address": None,
        "okved_main": None,
        "okved_add": [],
        "msp_category": _MSP_CATEGORIES.get(elem.get("КатСубМСП", ""), None),
        "msp_since": _iso_date(elem.get("ДатаВклМСП", "")),
    }
    location_parts: list[str] = []
    for child in elem.iter():
        tag = _local(child.tag)
        if tag == "ОргВклМСП":
            doc["kind"] = "ЮЛ"
            doc["inn"] = child.get("ИННЮЛ")
            doc["ogrn"] = child.get("ОГРН")
            doc["name"] = child.get("НаимОрг")
            doc["name_short"] = child.get("НаимОргСокр")
        elif tag == "ИПВклМСП":
            doc["kind"] = "ИП"
            doc["inn"] = child.get("ИННФЛ")
            doc["ogrn"] = child.get("ОГРНИП")
        elif tag == "ФИОИП":
            fio = " ".join(
                filter(None, (child.get("Фамилия"), child.get("Имя"), child.get("Отчество")))
            )
            doc["name"] = f"ИП {fio}".strip()
        elif tag == "СведМН":
            doc["region_code"] = child.get("КодРегион")
        elif tag in ("Регион", "Район", "Город", "НаселПункт"):
            name = child.get("Наим")
            type_ = child.get("Тип")
            if name:
                part = f"{type_} {name}".strip() if type_ else name
                if part not in location_parts:
                    location_parts.append(part)
        elif tag == "СвОКВЭДОсн":
            doc["okved_main"] = child.get("КодОКВЭД")
        elif tag == "СвОКВЭДДоп":
            code = child.get("КодОКВЭД")
            if code:
                doc["okved_add"].append(code)
    if location_parts:
        doc["address"] = ", ".join(location_parts)
    return doc if doc["inn"] else None


def _iter_xml(stream: IO[bytes]) -> Iterator[dict]:
    """Потоково выдаёт документы из одного XML-файла реестра."""
    for _event, elem in ET.iterparse(stream, events=("end",)):
        if _local(elem.tag) == "Документ":
            doc = _parse_document(elem)
            if doc:
                yield doc
            elem.clear()


def iter_companies(
    path: str | Path,
    region_code: str,
    okved_prefixes: tuple[str, ...],
    include_ip: bool = False,
) -> Iterator[dict]:
    """Компании нужного региона с подходящим ОКВЭД из ZIP-выгрузки или XML-файла.

    Совпадение ОКВЭД проверяется и по основному, и по дополнительным кодам.
    """
    path = Path(path)

    def matches(doc: dict) -> bool:
        if doc["region_code"] != region_code:
            return False
        if doc["kind"] == "ИП" and not include_ip:
            return False
        if okved_matches(doc.get("okved_main") or "", okved_prefixes):
            return True
        return any(okved_matches(code, okved_prefixes) for code in doc.get("okved_add") or [])

    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".xml")]
            total = len(names)
            for idx, name in enumerate(names, 1):
                if idx % 200 == 0 or idx == total:
                    print(f"[rsmp] обработано файлов: {idx}/{total}")
                with zf.open(name) as fh:
                    for doc in _iter_xml(fh):
                        if matches(doc):
                            yield doc
    else:
        with open(path, "rb") as fh:
            for doc in _iter_xml(fh):
                if matches(doc):
                    yield doc
