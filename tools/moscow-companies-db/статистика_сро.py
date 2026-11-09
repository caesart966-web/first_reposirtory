"""Статистика по всем строительным СРО России — из полной выгрузки реестра НОСТРОЙ.

Все строительные СРО ведут членов в едином реестре НОСТРОЙ: у каждой записи
есть СРО, статус («является членом» / «исключен»), дата вступления и дата
выхода. Поэтому реестр выкачивается один раз целиком, а всё остальное
считается здесь, без запросов в сеть.

ЗАПУСК (из папки со скриптами):

    python москва_стройка.py нострой --заново    # выкачать реестр целиком (около часа)
    python статистика_сро.py                      # → СРО_России.xlsx

Листы:
  «Сводная» — одна строка на СРО, колонки как в файле по Петербургу
  (SPB_SRO_…xlsx): всего записей, действующих, исключённых, вступило
  и исключено по годам, без даты исключения; плюс регион и итог по России.
  «Вступления по месяцам», «Исключения по месяцам» — СРО × месяц.
  «По регионам» — то же, сложенное по субъектам РФ.
  «Как считали» — источник, дата, полнота выгрузки.

Регион СРО — субъект, где зарегистрировано больше всего её действующих
членов: у строительных СРО действует региональный принцип, и своего адреса
СРО в записи реестра нет.

--с-членами дополнительно пишет СРО_России_члены.xlsx: лист на каждую СРО
(ИНН, название, статус, даты), как в файле по Петербургу. Файл большой.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

_ЗДЕСЬ = Path(__file__).resolve().parent


def _модуль(имя: str, файл: str):
    spec = importlib.util.spec_from_file_location(имя, _ЗДЕСЬ / файл)
    модуль = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(модуль)
    return модуль


стройка = _модуль("москва_стройка", "москва_стройка.py")


def записи(дамп: Path) -> list[dict]:
    """Записи выгрузки без повторов (повторы бывают после продолжения с обрыва)."""
    видели, итог = set(), []
    for r in стройка.читать_дамп(дамп):
        k = стройка.ключ_записи(r)
        if k not in видели:
            видели.add(k)
            итог.append(r)
    return итог


def ключ_сро(r: dict) -> str:
    return (r.get("sro_num") or r.get("sro") or r.get("sro_id") or "").strip() or "СРО не указана"


def _номер_для_сортировки(номер: str) -> tuple:
    m = re.search(r"С-(\d+)", номер.upper().replace("C", "С"))
    return (int(m.group(1)) if m else 10 ** 6, номер)


def _год(iso: str | None) -> int | None:
    return int(iso[:4]) if iso and re.match(r"\d{4}-", iso) else None


def _месяц(iso: str | None) -> str | None:
    return iso[:7] if iso and re.match(r"\d{4}-\d{2}", iso) else None


def месяцы(с_года: int, по: date) -> list[str]:
    return [f"{г}-{м:02d}" for г in range(с_года, по.year + 1) for м in range(1, 13)
            if (г, м) <= (по.year, по.month)]


def посчитать(все: list[dict], годы: list[int], список_месяцев: list[str]) -> list[dict]:
    """Одна строка на СРО со всеми числами."""
    по_сро: dict[str, list[dict]] = defaultdict(list)
    for r in все:
        по_сро[ключ_сро(r)].append(r)
    строки = []
    for ключ, рр in по_сро.items():
        действующие = [r for r in рр if not r.get("former")]
        исключённые = [r for r in рр if r.get("former")]
        имя = Counter(r.get("sro_short") or r.get("sro") or "" for r in рр).most_common(1)[0][0]
        регионы = Counter(r.get("region") for r in (действующие or рр) if r.get("region"))
        строки.append({
            "номер": ключ if ключ.upper().startswith(("СРО", "SRO")) else (рр[0].get("sro_num") or ""),
            "имя": имя or ключ,
            "регион": регионы.most_common(1)[0][0] if регионы else "",
            "всего": len(рр), "действующих": len(действующие), "исключённых": len(исключённые),
            "вступило": {г: sum(1 for r in рр if _год(r.get("start")) == г) for г in годы},
            "исключено": {г: sum(1 for r in исключённые if _год(r.get("stop")) == г) for г in годы},
            "без_даты": sum(1 for r in исключённые if not r.get("stop")),
            "вступило_м": Counter(_месяц(r.get("start")) for r in рр),
            "исключено_м": Counter(_месяц(r.get("stop")) for r in исключённые),
            "члены": рр,
        })
    строки.sort(key=lambda s: _номер_для_сортировки(s["номер"] or s["имя"]))
    return строки


# -- Excel -----------------------------------------------------------------

def записать(out: Path, строки: list[dict], годы: list[int], список_месяцев: list[str],
             сведения: list[tuple[str, str]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter as L

    ШАПКА = PatternFill("solid", fgColor="1F4E79")
    ИТОГ = PatternFill("solid", fgColor="DDEBF7")
    wb = Workbook()

    def шапка(ws, колонки, ширины):
        ws.append(колонки)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = ШАПКА
            c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        ws.row_dimensions[1].height = 32
        for i, w in enumerate(ширины, 1):
            ws.column_dimensions[L(i)].width = w

    def итог(ws, подпись_кол, первая_числовая, последняя, строк):
        n = строк + 1
        ws.append([])
        row = n + 1
        ws.cell(row=row, column=подпись_кол, value="Итого по России")
        for col in range(первая_числовая, последняя + 1):
            ws.cell(row=row, column=col, value=f"=SUM({L(col)}2:{L(col)}{n})")
        for c in ws[row]:
            c.font = Font(bold=True)
            c.fill = ИТОГ

    # «Сводная» — колонки как в файле по Петербургу, плюс регион
    ws = wb.active
    ws.title = "Сводная"
    g1, g2 = годы[0], годы[-1]
    кол = (["Рег. номер", "СРО", "Регион", "Всего записей", "Действующих", "Исключённых (всего)"]
           + [f"Вступило {г}" for г in годы] + [f"Вступило {g1}–{g2}"]
           + [f"Исключено {г}" for г in годы] + [f"Исключено {g1}–{g2}"] + ["Без даты искл."])
    шапка(ws, кол, [20, 40, 24, 11, 11, 13] + [11] * (2 * len(годы) + 3))
    п_вст = 7                                   # первая колонка «Вступило <год>»
    п_иск = п_вст + len(годы) + 1
    for i, s in enumerate(строки, 2):
        ws.append([s["номер"], s["имя"], s["регион"], s["всего"], s["действующих"], s["исключённых"]]
                  + [s["вступило"][г] for г in годы]
                  + [f"=SUM({L(п_вст)}{i}:{L(п_вст + len(годы) - 1)}{i})"]
                  + [s["исключено"][г] for г in годы]
                  + [f"=SUM({L(п_иск)}{i}:{L(п_иск + len(годы) - 1)}{i})"]
                  + [s["без_даты"]])
    итог(ws, 2, 4, len(кол), len(строки))
    ws.cell(row=len(строки) + 3, column=1, value=f"СРО: {len(строки)}").font = Font(bold=True)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{L(len(кол))}{len(строки) + 1}"

    # помесячные листы
    for название, ключ in (("Вступления по месяцам", "вступило_м"), ("Исключения по месяцам", "исключено_м")):
        w = wb.create_sheet(название)
        шапка(w, ["Рег. номер", "СРО", "Регион"] + список_месяцев, [20, 40, 24] + [8] * len(список_месяцев))
        for s in строки:
            w.append([s["номер"], s["имя"], s["регион"]] + [s[ключ].get(м, 0) for м in список_месяцев])
        итог(w, 2, 4, 3 + len(список_месяцев), len(строки))
        w.freeze_panes = "D2"

    # по регионам
    w = wb.create_sheet("По регионам")
    кол_р = (["Регион", "СРО", "Всего записей", "Действующих", "Исключённых (всего)"]
             + [f"Вступило {г}" for г in годы] + [f"Исключено {г}" for г in годы])
    шапка(w, кол_р, [30, 8, 11, 11, 13] + [11] * (2 * len(годы)))
    регионы: dict[str, list[dict]] = defaultdict(list)
    for s in строки:
        регионы[s["регион"] or "регион не определён"].append(s)
    for рег in sorted(регионы, key=lambda р: -sum(s["действующих"] for s in регионы[р])):
        сс = регионы[рег]
        w.append([рег, len(сс), sum(s["всего"] for s in сс), sum(s["действующих"] for s in сс),
                  sum(s["исключённых"] for s in сс)]
                 + [sum(s["вступило"][г] for s in сс) for г in годы]
                 + [sum(s["исключено"][г] for s in сс) for г in годы])
    итог(w, 1, 2, len(кол_р), len(регионы))
    w.freeze_panes = "B2"

    # как считали
    w = wb.create_sheet("Как считали")
    w.column_dimensions["A"].width = 34
    w.column_dimensions["B"].width = 100
    for подпись, текст in сведения:
        w.append([подпись, текст])
        w.cell(row=w.max_row, column=1).font = Font(bold=True)
        w.cell(row=w.max_row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    # итоги — формулы; Excel пересчитает их при открытии файла
    from openpyxl.workbook.properties import CalcProperties
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.save(out)


def записать_членов(out: Path, строки: list[dict]) -> None:
    from openpyxl import Workbook
    wb = Workbook(write_only=True)
    занятые: set[str] = set()
    for s in строки:
        имя = re.sub(r"^СРО-", "", s["номер"] or s["имя"])[:31] or "СРО"
        имя = re.sub(r"[\[\]:*?/\\]", "_", имя)
        база, n = имя, 2
        while имя in занятые:
            имя = f"{база[:28]}_{n}"
            n += 1
        занятые.add(имя)
        ws = wb.create_sheet(имя)
        ws.append(["ИНН", "Название", "Статус", "Дата вступления", "Дата исключения"])
        for r in sorted(s["члены"], key=lambda r: (r.get("name") or "").lower()):
            ws.append([r.get("inn"), r.get("name"), (r.get("status") or "").lower(),
                       r.get("start"), r.get("stop") if r.get("former") else None])
    wb.save(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Статистика по всем строительным СРО России (реестр НОСТРОЙ)")
    p.add_argument("--дамп", default=стройка.ДАМП, help="выгрузка реестра (москва_стройка.py нострой)")
    p.add_argument("--out", default="СРО_России.xlsx")
    p.add_argument("--с-года", dest="с_года", type=int, default=2023, help="первый год в колонках")
    p.add_argument("--с-членами", dest="с_членами", action="store_true",
                   help="ещё и СРО_России_члены.xlsx — лист со списком членов на каждую СРО")
    args = p.parse_args(argv)

    дамп = Path(args.дамп)
    if not дамп.exists():
        print(f"Нет выгрузки {дамп}. Сначала: python москва_стройка.py нострой --заново", file=sys.stderr)
        return 1
    состояние_путь = стройка._состояние(дамп)
    состояние = json.loads(состояние_путь.read_text(encoding="utf-8")) if состояние_путь.exists() else {}
    все = записи(дамп)
    if not все:
        print(f"Выгрузка {дамп} пустая. Запустите: python москва_стройка.py нострой --заново", file=sys.stderr)
        return 1
    if not any("name" in r for r in все[:1000]):
        print("Выгрузка сделана старой версией — в ней нет названий компаний и регионов. "
              "Перекачайте: python москва_стройка.py нострой --заново", file=sys.stderr)
        return 1
    if not состояние.get("готово"):
        print("[сро] ВНИМАНИЕ: выгрузка не закончена — допустите её той же командой "
              "(python москва_стройка.py нострой), иначе цифры будут занижены", file=sys.stderr)

    сегодня = date.today()
    годы = list(range(args.с_года, сегодня.year + 1))
    список_месяцев = месяцы(args.с_года, сегодня)
    строки = посчитать(все, годы, список_месяцев)

    заявлено = состояние.get("всего")
    доля = f"{len(все) / заявлено * 100:.1f} %" if заявлено else "неизвестно"
    сведения = [
        ("Источник", "Единый реестр членов строительных СРО — reestr.nostroy.ru (НОСТРОЙ), "
                     "выгрузка целиком: москва_стройка.py нострой"),
        ("Дата выгрузки", состояние.get("дата") or "неизвестно"),
        ("Полнота выгрузки", f"получено {len(все)} записей из заявленных реестром "
                             f"{заявлено or '?'} ({доля})"),
        ("Запись", "одно членство компании в одной СРО; компания, бывшая в нескольких СРО, "
                   "считается в каждой"),
        ("Действующие", "статус «является членом» (и другие, кроме «исключен»/«прекращено»)"),
        ("Вступило <год / месяц>", "по дате вступления (registry_registration_date) — "
                                   "и у тех, кто потом вышел"),
        ("Исключено <год / месяц>", "по дате прекращения членства у исключённых"),
        ("Регион СРО", "субъект, где зарегистрировано больше всего её действующих членов"),
        ("Посчитано", f"{сегодня:%d.%m.%Y}, статистика_сро.py"),
    ]
    out = Path(args.out)
    записать(out, строки, годы, список_месяцев, сведения)
    действующих = sum(s["действующих"] for s in строки)
    print(f"[сро] СРО: {len(строки)}; записей: {len(все)} (полнота {доля}); "
          f"действующих членств: {действующих} → {out}")
    if заявлено and len(все) < заявлено * 0.99:
        print("[сро] ВНИМАНИЕ: выгрузка неполная (меньше 99 % заявленного) — цифры занижены. "
              "Повторите: python москва_стройка.py нострой", file=sys.stderr)
    if args.с_членами:
        out2 = out.with_name(out.stem + "_члены.xlsx")
        записать_членов(out2, строки)
        print(f"[сро] списки членов по СРО → {out2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
