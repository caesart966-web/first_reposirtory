"""Председатели советов СРО — с сайтов самих СРО.

Ни в реестрах НОСТРОЙ и НОПРИЗ, ни в ЕГРЮЛ (Checko) председателя постоянно
действующего коллегиального органа (совета) нет: там только руководитель
исполнительного органа. Состав совета СРО обязана раскрывать на своём сайте,
поэтому скрипт обходит сайт каждой СРО: главную и страницы, похожие на
«Совет», «Органы управления», «Руководство», «О нас», — и ищет рядом со словами
«Председатель Совета» (или «Правления») фамилию, имя и отчество.

Найденное — не истина, а находка: рядом всегда записаны адрес страницы и кусок
текста, по которым её проверяют глазами. Не найдено — сайт не открылся, всё
на картинках или в скриптах, или председателя на сайте нет.

Файл с колонками «Рег. номер», «СРО», «Сайт» готовит сро_россия.py
(--для-председателей). Прогон дописывает колонки в тот же файл; повторный
запуск обходит только необработанные строки.

  python председатели_сро.py --file сро_председатели.xlsx
  python председатели_сро.py --file сро_председатели.xlsx --заново   # пройти всё снова
"""
from __future__ import annotations

import argparse
import re
import sys
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

ИСХ = ["Рег. номер", "СРО", "Вид", "Регион", "ИНН", "Сайт"]
НОВЫЕ = ["Председатель совета", "Как назван на сайте", "Где найдено", "Фрагмент", "Сайт: итог"]
ИТОГ = "Сайт: итог"
СТРАНИЦ = 12          # не больше страниц одного сайта
ТАЙМАУТ = 20

# по этим словам в ссылке или её тексте страница похожа на ту, где пишут о совете
_ССЫЛКА = re.compile(r"совет|орган[ыа]? управлени|руководств|структур|о нас|об ассоциаци|о союзе|"
                     r"о партнерств|об организаци|о сро|состав|президиум|правлени|"
                     r"sovet|council|rukovod|upravl|struktur|about|o-nas|organy|board|management|"
                     r"o-sro|ob-associ|o-soyuz|kollegial|presid", re.I)
_ДОЛЖНОСТЬ = re.compile(r"(?<![а-яё])(председател[ьяюем]+)\s+(совета|правления|наблюдательного\s+совета|"
                        r"постоянно\s+действующего\s+коллегиального\s+органа(?:\s+управления)?)", re.I)
# «Председатель Совета Федерации», «…Совета директоров», «…Совета НОСТРОЙ» — чужой совет, не этой СРО
_ЧУЖОЙ = re.compile(r"\s*(федерации|министров|безопасности|ветеранов|директоров|ностро|нопри|национальн|"
                    r"рспп|тпп|торгово|муниципальн|депутат|при\s|по\s|молод[её]жн|общественн|"
                    r"[а-яё]+ской\s+(?:области|республики)|[а-яё]+ского\s+края)", re.I)
_ЗАМ = re.compile(r"(заместител\w*|зам\.|и\.\s*о\.|врио|исполняющ\w*)\s*$", re.I)
# Фамилия Имя Отчество (отчество — по окончанию), или Фамилия И. О., или И. О. Фамилия
_ОТЧ = r"[А-ЯЁ][а-яё]+(?:вич|вна|ична|инична|ич|оглы|кызы)"
_СЛОВО = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?"
_ФИО = re.compile(rf"({_СЛОВО})\s+({_СЛОВО})\s+({_ОТЧ})(?![а-яё])"
                  rf"|({_СЛОВО})\s+([А-ЯЁ])\.\s*([А-ЯЁ])\.(?![а-яё])"
                  rf"|([А-ЯЁ])\.\s*([А-ЯЁ])\.\s*({_СЛОВО})(?![а-яё])")
# слова, которые выглядят как фамилия, но ею не бывают (заголовки, названия)
_НЕ_ФАМИЛИЯ = {"Совета", "Совет", "Председатель", "Председателя", "Ассоциации", "Ассоциация", "Союза",
               "Союз", "Саморегулируемой", "Организации", "Российской", "Федерации", "Член", "Члены",
               "Генеральный", "Директор", "Президент", "Состав", "Правления", "Партнерства"}


class _Текст(HTMLParser):
    """Текст страницы и ссылки (адрес, текст ссылки) — без сторонних библиотек."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.части: list[str] = []
        self.ссылки: list[tuple[str, str]] = []
        self._ссылка: str | None = None
        self._текст_ссылки: list[str] = []
        self._пропуск = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._пропуск += 1
        elif tag == "a":
            self._ссылка = dict(attrs).get("href")
            self._текст_ссылки = []
        elif tag in ("br", "p", "div", "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "section"):
            self.части.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._пропуск = max(0, self._пропуск - 1)
        elif tag == "a" and self._ссылка is not None:
            self.ссылки.append((self._ссылка, " ".join(self._текст_ссылки)))
            self._ссылка = None

    def handle_data(self, data):
        if self._пропуск:
            return
        self.части.append(data)
        if self._ссылка is not None:
            self._текст_ссылки.append(data.strip())

    def текст(self) -> str:
        return re.sub(r"[ \t\r\f\v\xa0]+", " ", "".join(self.части))


def разобрать(html: str) -> tuple[str, list[tuple[str, str]]]:
    p = _Текст()
    try:
        p.feed(html)
    except Exception:  # noqa: BLE001 — кривой HTML: берём, что успели
        pass
    return p.текст(), p.ссылки


def _фио(м: re.Match) -> str | None:
    г = м.groups()
    if г[0]:
        ф, и, о = г[0], г[1], г[2]
        if ф in _НЕ_ФАМИЛИЯ or и in _НЕ_ФАМИЛИЯ:
            return None
        return f"{ф} {и} {о}"
    if г[3]:
        return None if г[3] in _НЕ_ФАМИЛИЯ else f"{г[3]} {г[4]}. {г[5]}."
    return None if г[8] in _НЕ_ФАМИЛИЯ else f"{г[8]} {г[6]}. {г[7]}."


def найти(текст: str) -> tuple[str, str, str] | None:
    """(ФИО, как назван, фрагмент) — председатель совета в тексте страницы."""
    лучшее = None
    for м in _ДОЛЖНОСТЬ.finditer(текст):
        до = текст[max(0, м.start() - 40):м.start()]
        if _ЗАМ.search(до):
            continue                                   # заместитель председателя — не он
        if м.group(2).lower().startswith("совета") and _ЧУЖОЙ.match(текст[м.end():м.end() + 60]):
            continue
        как = " ".join(м.group(0).split())
        после = текст[м.end():м.end() + 220]
        кандидаты = []
        for ф in _ФИО.finditer(после):
            имя = _фио(ф)
            if имя:
                кандидаты.append((ф.start(), имя))
                break
        перед = текст[max(0, м.start() - 160):м.start()]
        for ф in _ФИО.finditer(перед):
            имя = _фио(ф)
            if имя:
                # ФИО прямо перед должностью: «Иванов Иван Иванович — Председатель Совета»
                кандидаты.append((len(перед) - ф.end() + 30, имя))
        if not кандидаты:
            continue
        расстояние, имя = min(кандидаты)
        фрагмент = " ".join(текст[max(0, м.start() - 60):м.end() + 120].split())
        полное = имя.count(".") == 0
        оценка = (0 if полное else 1, расстояние)
        if лучшее is None or оценка < лучшее[0]:
            лучшее = (оценка, (имя, как[:1].upper() + как[1:].lower(), фрагмент))
    return лучшее[1] if лучшее else None


def адреса(сайт: str) -> list[str]:
    """«https://a.ru/;  www.b.ru» → ['https://a.ru/', 'http://www.b.ru']."""
    out = []
    for s in re.split(r"[\s;,]+", str(сайт or "")):
        s = s.strip()
        if not s or "." not in s:
            continue
        if not re.match(r"https?://", s, re.I):
            s = "http://" + s
        out.append(s)
    return out


_поток = threading.local()


def _сессия() -> requests.Session:
    if not hasattr(_поток, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                          "Accept-Language": "ru-RU,ru;q=0.9"})
        _поток.s = s
    return _поток.s


def скачать(url: str) -> tuple[str, str] | None:
    """(итоговый адрес, html) или None. У российских сайтов бывают сертификаты Минцифры,
    которых нет в стандартном наборе Python, — тогда вторая попытка без проверки сертификата
    (страницы публичные, ничего не отправляем)."""
    for проверять in (True, False):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = _сессия().get(url, timeout=ТАЙМАУТ, verify=проверять, allow_redirects=True)
            if r.status_code >= 400 or "html" not in r.headers.get("content-type", "html"):
                return None
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = r.apparent_encoding
            return r.url, r.text
        except requests.exceptions.SSLError:
            continue
        except requests.RequestException:
            return None
    return None


def обойти(сайт: str, скачать=скачать) -> dict:
    """Ищет председателя на главной и на похожих страницах одного сайта."""
    старт = адреса(сайт)
    if not старт:
        return {ИТОГ: "сайта нет"}
    очередь, видели, открылось = list(старт), set(), 0
    домены = {urlparse(u).netloc.removeprefix("www.") for u in старт}
    while очередь and len(видели) < СТРАНИЦ:
        url = очередь.pop(0)
        if url in видели:
            continue
        видели.add(url)
        ответ = скачать(url)
        if not ответ:
            continue
        открылось += 1
        итоговый, html = ответ
        домены.add(urlparse(итоговый).netloc.removeprefix("www."))
        текст, ссылки = разобрать(html)
        if (нашли := найти(текст)):
            имя, как, фрагмент = нашли
            return {"Председатель совета": имя, "Как назван на сайте": как, "Где найдено": итоговый,
                    "Фрагмент": фрагмент[:300], ИТОГ: "найдено"}
        # сначала страницы про совет, потом остальные похожие
        похожие = []
        for href, подпись in ссылки:
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            полный = urljoin(итоговый, href).split("#")[0]
            if urlparse(полный).netloc.removeprefix("www.") not in домены:
                continue
            if re.search(r"\.(pdf|docx?|xlsx?|jpe?g|png|zip|rar)$", полный, re.I):
                continue
            ключ = f"{подпись} {полный}"
            if _ССЫЛКА.search(ключ):
                похожие.append((0 if re.search(r"совет|sovet|council", ключ, re.I) else 1, полный))
        for _, полный in sorted(похожие):
            if полный not in видели and полный not in очередь:
                очередь.append(полный)
    if not открылось:
        return {ИТОГ: "сайт не открылся"}
    return {ИТОГ: f"не найдено (страниц просмотрено: {len(видели)})"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default="сро_председатели.xlsx")
    ap.add_argument("--потоков", type=int, default=8)
    ap.add_argument("--заново", action="store_true", help="обойти и уже обработанные строки")
    a = ap.parse_args(argv)
    from openpyxl import Workbook, load_workbook
    путь = Path(a.file)
    ws = load_workbook(путь).active
    строки = list(ws.iter_rows(values_only=True))
    шапка = [str(c or "") for c in строки[0]]
    записи = [dict(zip(шапка, ["" if v is None else v for v in r])) for r in строки[1:] if any(r)]
    колонки = шапка + [к for к in НОВЫЕ if к not in шапка]
    нужно = [z for z in записи if a.заново or not str(z.get(ИТОГ) or "").strip()]
    print(f"СРО в файле: {len(записи)}, обойти: {len(нужно)}", flush=True)
    замок = threading.Lock()
    готово = [0]

    def сохранить():
        wb = Workbook()
        w = wb.active
        w.title = "Председатели"
        w.append(колонки)
        for z in записи:
            w.append([z.get(к, "") for к in колонки])
        try:
            wb.save(путь)
        except PermissionError:
            print(f"Не могу записать {путь}: файл открыт в Excel. Закройте его — сохраню на следующем шаге.",
                  file=sys.stderr)

    def одна(z):
        итог = обойти(str(z.get("Сайт") or ""))
        with замок:
            for к in НОВЫЕ:
                z[к] = итог.get(к, "")
            готово[0] += 1
            print(f"  {готово[0]}/{len(нужно)} {z.get('Рег. номер')}: "
                  f"{итог.get('Председатель совета') or итог[ИТОГ]}", flush=True)
            if готово[0] % 20 == 0:
                сохранить()

    начало = time.time()
    with ThreadPoolExecutor(max_workers=a.потоков) as pool:
        list(pool.map(одна, нужно))
    сохранить()
    найдено = sum(1 for z in записи if z.get(ИТОГ) == "найдено")
    print(f"Готово за {int(time.time() - начало)} с: председатель найден у {найдено} из {len(записи)} → {путь}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
