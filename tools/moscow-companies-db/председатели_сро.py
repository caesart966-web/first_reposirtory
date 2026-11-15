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
СТРАНИЦ = 30          # не больше страниц одного сайта (с 12 — у 102 сайтов из 442 не хватило)
ТАЙМАУТ = 20

# по этим словам в ссылке или её тексте страница похожа на ту, где пишут о совете
_ССЫЛКА = re.compile(r"совет|орган[ыа]? управлени|руководств|структур|о нас|об ассоциаци|о союзе|"
                     r"о партнерств|об организаци|о сро|состав|президиум|правлени|"
                     r"sovet|council|rukovod|upravl|struktur|about|o-nas|organy|board|management|"
                     r"o-sro|ob-associ|o-soyuz|kollegial|presid", re.I)
_ДОЛЖНОСТЬ = re.compile(r"(?<![а-яё])(председател[ьяюем]+)\s+(совета|правления|наблюдательного\s+совета|"
                        r"постоянно\s+действующего\s+коллегиального\s+органа(?:\s+управления)?)", re.I)
# «Председатель Совета Федерации», «…Совета директоров», «…Совета НОСТРОЙ», «председатель правления
# Тамбовского регионального отделения…» — чужой совет или правление, не этой СРО
_ЧУЖОЙ = re.compile(r"\s*(федерации|министров|безопасности|ветеранов|директоров|ностро|нопри|национальн|"
                    r"рспп|тпп|торгово|муниципальн|депутат|при\s|по\s|молод[её]жн|общественн|банк|"
                    r"ооо|оао|зао|пао|ао\s|[а-яё]+ской\s+(?:области|республики)|[а-яё]+ского\s+края|"
                    r"[а-яё]+(?:ского|ской|ного)\s+(?:регионального|областного|городского|отделени|"
                    r"общественн|организаци))", re.I)
_АББР = re.compile(r"\s*[А-ЯЁ]{5,}\s+России")            # «председатель Правления ХКОООСА России»
# между должностью и именем — значит, имя не к ней: другой раздел, сотрудники аппарата, чужая организация
_ЛИШНЕЕ = re.compile(r"отделени|регионал|общественн|аппарат|дирекци|сотрудник|контакт", re.I)
_ЗАМ = re.compile(r"(заместител\w*|зам\.|и\.\s*о\.|врио|исполняющ\w*|перв\w+|бывш\w+|почет\w+|почёт\w+|"
                  r"прежн\w+|экс-?)\s*$", re.I)
# Фамилия Имя Отчество (отчество — по окончанию), или Фамилия И. О., или И. О. Фамилия
_ОТЧ = r"[А-ЯЁа-яё][а-яё]+(?:вич|вна|ична|инична|ич|оглы|кызы)"
_СЛОВО = r"[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?"
_ФИО = re.compile(rf"({_СЛОВО})\s+({_СЛОВО})\s+({_ОТЧ})(?![а-яё])"
                  rf"|({_СЛОВО})\s+({_ОТЧ})\s+({_СЛОВО})(?![а-яё])"
                  rf"|({_СЛОВО})\s+([А-ЯЁ])\.\s*([А-ЯЁ])\.(?![а-яё])"
                  rf"|([А-ЯЁ])\.\s*([А-ЯЁ])\.\s*({_СЛОВО})(?![а-яё])")
# слова, которые выглядят как фамилия, но ею не бывают (заголовки, названия)
_НЕ_ФАМИЛИЯ = {"Совета", "Совет", "Председатель", "Председателя", "Ассоциации", "Ассоциация", "Союза",
               "Союз", "Саморегулируемой", "Организации", "Российской", "Федерации", "Член", "Члены",
               "Генеральный", "Директор", "Президент", "Состав", "Правления", "Партнерства",
               "Независимый", "Независимая", "Исполнительный", "Индивидуальный", "Представитель",
               "Протокол", "Дата", "Решением", "Избран", "Избрана", "Общества", "Общество"}


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
    """«Фамилия Имя Отчество» из любого из четырёх видов записи."""
    г = [x[:1].upper() + x[1:] if x else x for x in м.groups()]
    if г[0]:
        ф, и, о = г[0], г[1], г[2]
        if ф in _НЕ_ФАМИЛИЯ or и in _НЕ_ФАМИЛИЯ:
            return None
        return f"{ф} {и} {о}"
    if г[3]:                                           # Имя Отчество Фамилия
        и, о, ф = г[3], г[4], г[5]
        if ф in _НЕ_ФАМИЛИЯ or и in _НЕ_ФАМИЛИЯ:
            return None
        return f"{ф} {и} {о}"
    if г[6]:
        return None if г[6] in _НЕ_ФАМИЛИЯ else f"{г[6]} {г[7]}. {г[8]}."
    return None if г[11] in _НЕ_ФАМИЛИЯ else f"{г[11]} {г[9]}. {г[10]}."


def найти(текст: str) -> tuple[str, str, str] | None:
    """(ФИО, как назван, фрагмент) — председатель совета в тексте страницы."""
    лучшее = None
    for м in _ДОЛЖНОСТЬ.finditer(текст):
        до = текст[max(0, м.start() - 40):м.start()]
        if _ЗАМ.search(до):
            continue                                   # заместитель председателя — не он
        хвост = текст[м.end():м.end() + 60]
        if _ЧУЖОЙ.match(хвост) or _АББР.match(хвост):
            continue
        как = " ".join(м.group(0).split())
        скобка = bool(re.match(r"\s*\)", хвост))
        после = текст[м.end():м.end() + 220]
        кандидаты = []
        перед = текст[max(0, м.start() - 160):м.start()]
        последнее = None
        for ф in _ФИО.finditer(перед):
            if _фио(ф):
                последнее = ф
        # ФИО прямо перед должностью: «Иванов Иван Иванович — Председатель Совета»; но не
        # «Иванов Иван Иванович — независимый член, председатель правления другой организации»
        if последнее is not None and not re.search(r"член|\n\s*\n", перед[последнее.end():], re.I):
            между = перед[последнее.end():]
            # вплотную («Иванов И. И. – председатель Совета, директор ООО…») — это его должность
            вплотную = re.fullmatch(r"[ \t]*[–—-]?[ \t]*", между) is not None
            строкой_выше = not вплотную and not между.strip()   # «Иванов И. И.» / «Председатель Совета»
            кандидаты.append((len(между) if вплотную else 15 if строкой_выше else len(между) + 30,
                              _фио(последнее)))
        # «2) Петров … (председатель Совета); 3) Сидоров …» — должность в скобках относится к имени
        # перед ней; если имени перед ней нет («Президент (Председатель правления) Петров») — к следующему
        if not (скобка and кандидаты):
            for ф in _ФИО.finditer(после):
                имя = _фио(ф)
                if not имя:
                    continue
                # первое имя после должности; если между ними чужое — после должности имени нет
                до_имени = после[:ф.start()]
                if not _ЛИШНЕЕ.search(до_имени):
                    # «Председатель Совета: Иванов» / «– Иванов» / в той же строке — имя к должности;
                    # имя с новой строки без «:» и тире — скорее подпись к следующей должности
                    сразу = re.search(r"[:–—-]", до_имени) or "\n" not in до_имени
                    кандидаты.append((ф.start() if сразу else ф.start() + 20, имя))
                break
        if not кандидаты:
            continue
        расстояние, имя = min(кандидаты)
        фрагмент = " ".join(текст[max(0, м.start() - 60):м.end() + 120].split())
        полное = имя.count(".") == 0
        совет = "совет" in как.lower() or "коллегиальн" in как.lower()
        оценка = (0 if полное else 1, 0 if совет else 1, расстояние)
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
            тип = r.headers.get("content-type", "html")
            if r.status_code >= 400 or ("html" not in тип and "xml" not in тип):
                return None
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = r.apparent_encoding
            return r.url, r.text
        except requests.exceptions.SSLError:
            continue
        except requests.RequestException:
            return None
    return None


_ПРО_СОВЕТ = re.compile(r"совет|правлени|коллегиальн|президиум|орган[ыа]? управлени|"
                        r"sovet|pravlen|council|board|governance|kollegial|prezidium|organy|upravlen", re.I)
# типовые адреса страниц о совете — на сайтах, где меню рисует скрипт и ссылок в HTML нет
_ТИПОВЫЕ = ("sovet/", "pravlenie/", "about/sovet/", "o-nas/sovet/", "struktura/", "struktura/sovet",
            "struktura/pravlenie", "governance", "organy-upravleniya/", "rukovodstvo/", "about/",
            "o-nas/", "sro/struktura_sro/", "o-sro/", "ob-assotsiatsii/")


def обойти(сайт: str, скачать=скачать) -> dict:
    """Ищет председателя на главной и на похожих страницах одного сайта.

    Очередь — с приоритетом: сначала страницы, похожие на «Совет / Правление / Органы
    управления» (по ссылке, её тексту и карте сайта), потом остальные похожие. Найденное
    на такой странице принимается сразу; найденное на другой (главная, новости) — запасное,
    обход идёт дальше в поисках страницы про органы управления."""
    старт = адреса(сайт)
    if not старт:
        return {ИТОГ: "сайта нет"}
    очередь: list[tuple[int, int, str]] = [(1, i, u) for i, u in enumerate(старт)]
    счётчик, видели, открылось, запасное = len(старт), set(), 0, None
    домены = {urlparse(u).netloc.removeprefix("www.") for u in старт}
    типовые_добавлены = False

    def в_очередь(приоритет: int, url: str) -> None:
        nonlocal счётчик
        if url not in видели and all(u != url for _, _, u in очередь):
            очередь.append((приоритет, счётчик, url))
            счётчик += 1

    def итог(нашли, адрес) -> dict:
        имя, как, фрагмент = нашли
        return {"Председатель совета": имя, "Как назван на сайте": как, "Где найдено": адрес,
                "Фрагмент": фрагмент[:300], ИТОГ: "найдено"}

    while очередь and len(видели) < СТРАНИЦ:
        очередь.sort()
        приоритет, _, url = очередь.pop(0)
        if url in видели:
            continue
        видели.add(url)
        ответ = скачать(url)
        if not ответ:
            continue
        открылось += 1
        итоговый, html = ответ
        домены.add(urlparse(итоговый).netloc.removeprefix("www."))
        if url.endswith(".xml") or html.lstrip().startswith("<?xml"):
            for адрес in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", html)[:2000]:
                if адрес.endswith(".xml") or _ПРО_СОВЕТ.search(адрес):
                    в_очередь(0, адрес)            # вложенная карта сайта или страница про совет
            continue
        текст, ссылки = разобрать(html)
        if (нашли := найти(текст)):
            if приоритет == 0 or _ПРО_СОВЕТ.search(итоговый):
                return итог(нашли, итоговый)
            запасное = запасное or итог(нашли, итоговый)
        if not типовые_добавлены:
            типовые_добавлены = True
            корень = f"{urlparse(итоговый).scheme}://{urlparse(итоговый).netloc}/"
            в_очередь(0, корень + "sitemap.xml")
            for путь in _ТИПОВЫЕ:
                в_очередь(2, корень + путь)
        for href, подпись in ссылки:
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            полный = urljoin(итоговый, href).split("#")[0]
            if urlparse(полный).netloc.removeprefix("www.") not in домены:
                continue
            if re.search(r"\.(pdf|docx?|xlsx?|jpe?g|png|zip|rar)$", полный, re.I):
                continue
            ключ = f"{подпись} {полный}"
            if _ПРО_СОВЕТ.search(ключ):
                в_очередь(0, полный)
            elif _ССЫЛКА.search(ключ):
                в_очередь(1, полный)
    if запасное:
        return запасное
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
