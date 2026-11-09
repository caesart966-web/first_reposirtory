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


_ВСТУПЛЕНИЕ = set(стройка._ПОЛЯ_ВСТУПЛЕНИЯ)
_НАМЁК_ВЫХОДА = ("stop", "exclu", "suspen", "terminat", "end_date", "прекращ", "исключ")


def поле_выхода(все: list[dict]) -> tuple[str | None, bool, list[tuple[str, float, float]]]:
    """Какое поле записи — дата исключения: (поле, приблизительно ли, покрытие).

    В выгрузке НОСТРОЯ 10.11.2026 известные имена поля дали пустоту у всех
    276 тысяч исключённых, поэтому поле подбирается по данным: дата, которая
    есть почти у всех исключённых и почти ни у кого из действующих. Если такой
    нет — поле с «исключением» в имени, затем дата смены статуса, затем дата
    последнего изменения записи (last_updated) — две последние приблизительные.
    Покрытие — (поле, доля исключённых с ним, доля действующих с ним).
    """
    бывшие = [r for r in все if r.get("former")]
    действующие = [r for r in все if not r.get("former")]
    у_б = Counter(k for r in бывшие for k in (r.get("dates") or {}))
    у_д = Counter(k for r in действующие for k in (r.get("dates") or {}))
    покрытие = sorted(((k, у_б[k] / max(len(бывшие), 1), у_д[k] / max(len(действующие), 1))
                       for k in set(у_б) | set(у_д)), key=lambda x: (-x[1], x[0]))

    def имя(k: str) -> str:
        return k.split(".")[-1].lower()

    служебные = ("updated", "created", "modified", "inserted")
    for k, б, д in покрытие:
        if (имя(k) not in _ВСТУПЛЕНИЕ and not any(s in имя(k) for s in служебные)
                and б >= 0.5 and д <= 0.2):
            return k, False, покрытие
    for k, б, д in покрытие:
        if any(h in k.lower() for h in _НАМЁК_ВЫХОДА) and б >= 0.5:
            return k, False, покрытие
    for k, б, д in покрытие:
        if "status" in k.lower() and б >= 0.5:
            return k, True, покрытие
    for k, б, д in покрытие:
        if имя(k) == "last_updated" and б >= 0.5:
            return k, True, покрытие
    return None, False, покрытие


def выход(r: dict, поле: str | None) -> str | None:
    """Дата исключения записи: прямое поле выгрузки, иначе подобранное."""
    if not r.get("former"):
        return None
    return r.get("stop") or ((r.get("dates") or {}).get(поле) if поле else None)


def посчитать(все: list[dict], годы: list[int], список_месяцев: list[str],
              поле: str | None = None) -> list[dict]:
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
            "исключено": {г: sum(1 for r in исключённые if _год(выход(r, поле)) == г) for г in годы},
            "без_даты": sum(1 for r in исключённые if not выход(r, поле)),
            "вступило_м": Counter(_месяц(r.get("start")) for r in рр),
            "исключено_м": Counter(_месяц(выход(r, поле)) for r in исключённые),
            "члены": рр,
        })
    строки.sort(key=lambda s: _номер_для_сортировки(s["номер"] or s["имя"]))
    return строки


# -- Excel -----------------------------------------------------------------

МЕСЯЦЫ_РУС = ("Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август",
              "Сентябрь", "Октябрь", "Ноябрь", "Декабрь")
# Цвета серий — проверенная палитра (dataviz, references/palette.md): годы и
# «вступило / исключено» всегда одного цвета, порядок не меняется
ЦВЕТА = ("2A78D6", "EB6834", "1BAF7A", "EDA100", "E87BA4", "6250D6")


def записать(out: Path, строки: list[dict], годы: list[int], список_месяцев: list[str],
             сведения: list[tuple[str, str]], даты_исключения: bool = True,
             покрытие: list[tuple[str, float, float]] = ()) -> None:
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
    живые = sum(1 for s in строки if s["действующих"])
    ws.cell(row=len(строки) + 3, column=1,
            value=f"СРО: {len(строки)}, из них с действующими членами: {живые} "
                  f"(остальные исключены из госреестра СРО — их члены все бывшие)").font = Font(bold=True)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{L(len(кол))}{len(строки) + 1}"

    динамика(wb, строки, годы, список_месяцев, даты_исключения, L, шапка)

    # помесячные листы — с тепловой заливкой: где вступали много, ячейка синее
    from openpyxl.formatting.rule import ColorScaleRule
    for название, ключ in (("Вступления по месяцам", "вступило_м"), ("Исключения по месяцам", "исключено_м")):
        w = wb.create_sheet(название)
        шапка(w, ["Рег. номер", "СРО", "Регион"] + список_месяцев, [20, 40, 24] + [8] * len(список_месяцев))
        for s in строки:
            w.append([s["номер"], s["имя"], s["регион"]] + [s[ключ].get(м, 0) for м in список_месяцев])
        итог(w, 2, 4, 3 + len(список_месяцев), len(строки))
        w.freeze_panes = "D2"
        if строки and список_месяцев:
            w.conditional_formatting.add(
                f"D2:{L(3 + len(список_месяцев))}{len(строки) + 1}",
                ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="5598E7"))

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
    if покрытие:
        w.append([])
        w.append(["Поля с датами в выгрузке", "доля исключённых с этим полем · доля действующих"])
        w.cell(row=w.max_row, column=1).font = Font(bold=True)
        for k, б, д in покрытие[:25]:
            w.append([k, f"{б * 100:.1f} % · {д * 100:.1f} %"])
    # итоги — формулы; Excel пересчитает их при открытии файла
    from openpyxl.workbook.properties import CalcProperties
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.save(out)


def динамика(wb, строки, годы, список_месяцев, даты_исключения, L, шапка) -> None:
    """Лист «Динамика по России»: вступления месяц × год с графиком по годам
    и помесячная лента «вступило / исключено» со столбиками. Одна ось на график:
    вступления и исключения — одни и те же штуки, их можно ставить рядом."""
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.formatting.rule import ColorScaleRule
    from openpyxl.styles import Font, PatternFill

    w = wb.create_sheet("Динамика по России", 1)
    вступило = Counter()
    исключено = Counter()
    for s in строки:
        вступило.update(s["вступило_м"])
        исключено.update(s["исключено_м"])

    # 1) месяц × год
    шапка(w, ["Вступления по месяцам"] + [str(г) for г in годы], [24] + [10] * len(годы))
    последний = список_месяцев[-1] if список_месяцев else ""
    for м, имя in enumerate(МЕСЯЦЫ_РУС, 1):
        w.append([имя] + [вступило.get(f"{г}-{м:02d}", 0) if f"{г}-{м:02d}" <= последний else None
                          for г in годы])
    w.append(["За год"] + [f"=SUM({L(i)}2:{L(i)}13)" for i in range(2, len(годы) + 2)])
    for c in w[14]:
        c.font = Font(bold=True)
    w.conditional_formatting.add(f"B2:{L(len(годы) + 1)}13",
                                 ColorScaleRule(start_type="min", start_color="FFFFFF",
                                                end_type="max", end_color="5598E7"))
    w.cell(row=15, column=1, value=f"текущий месяц ({последний}) ещё не закончился").font = Font(
        italic=True, color="595959")

    график = LineChart()
    график.title = "Вступления в строительные СРО по месяцам"
    график.y_axis.title = "Вступлений"
    график.height, график.width = 9, 22
    данные = Reference(w, min_col=2, max_col=len(годы) + 1, min_row=1, max_row=13)
    график.add_data(данные, titles_from_data=True)
    график.set_categories(Reference(w, min_col=1, min_row=2, max_row=13))
    for n, серия in enumerate(график.series):
        серия.graphicalProperties.line.solidFill = ЦВЕТА[n % len(ЦВЕТА)]
        серия.graphicalProperties.line.width = 25400       # 2 пт
        серия.smooth = False
    график.x_axis.delete = False
    график.y_axis.delete = False
    график.legend.position = "b"
    w.add_chart(график, f"{L(len(годы) + 3)}1")

    # 2) лента по месяцам: вступило / исключено / прирост
    старт = 18
    w.cell(row=старт - 1, column=1, value="По месяцам подряд").font = Font(bold=True, size=12)
    заголовки = ["Месяц", "Вступило", "Исключено", "Прирост"]
    for j, h in enumerate(заголовки, 1):
        c = w.cell(row=старт, column=j, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E79")
    for i, м in enumerate(список_месяцев, старт + 1):
        w.cell(row=i, column=1, value=м)
        w.cell(row=i, column=2, value=вступило.get(м, 0))
        w.cell(row=i, column=3, value=исключено.get(м, 0) if даты_исключения else None)
        w.cell(row=i, column=4, value=f"=B{i}-C{i}" if даты_исключения else None)
    конец = старт + len(список_месяцев)
    for col in range(2, 5):
        w.column_dimensions[L(col)].width = max(w.column_dimensions[L(col)].width or 0, 12)
    if not даты_исключения:
        w.cell(row=конец + 1, column=1,
               value="Дат исключения в выгрузке нет — см. «Как считали»").font = Font(italic=True, color="C00000")

    столбики = BarChart()
    столбики.type = "col"
    столбики.title = "Вступило и исключено по месяцам" if даты_исключения else "Вступило по месяцам"
    столбики.y_axis.title = "Записей"
    столбики.height, столбики.width = 9, 30
    столбики.gapWidth = 40
    столбики.add_data(Reference(w, min_col=2, max_col=3 if даты_исключения else 2,
                                min_row=старт, max_row=конец), titles_from_data=True)
    столбики.set_categories(Reference(w, min_col=1, min_row=старт + 1, max_row=конец))
    for n, серия in enumerate(столбики.series):
        серия.graphicalProperties.solidFill = ЦВЕТА[n]
        серия.graphicalProperties.line.solidFill = ЦВЕТА[n]
    столбики.x_axis.delete = False
    столбики.y_axis.delete = False
    столбики.legend.position = "b"
    w.add_chart(столбики, f"F{старт}")
    w.freeze_panes = "B2"


def записать_членов(out: Path, строки: list[dict], поле: str | None = None) -> None:
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
                       r.get("start"), выход(r, поле)])
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
    поле, приблизительно, покрытие = поле_выхода(все)
    есть_прямые = any(r.get("stop") for r in все if r.get("former"))
    даты_исключения = есть_прямые or bool(поле)
    if not даты_исключения:
        print("[сро] ВНИМАНИЕ: дат исключения в выгрузке нет. Перекачайте свежей версией: "
              "python москва_стройка.py нострой --заново — она сохраняет все даты записи",
              file=sys.stderr)
    elif приблизительно:
        print(f"[сро] дата исключения — приблизительно, по полю «{поле}»", file=sys.stderr)
    строки = посчитать(все, годы, список_месяцев, поле)

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
        ("Исключено <год / месяц>",
         "по дате прекращения членства у исключённых" + (
             "" if есть_прямые else
             f" — поле «{поле}»" + (" (приблизительно: дата изменения записи)" if приблизительно else "")
             if поле else " — ДАТ В ВЫГРУЗКЕ НЕТ, колонки «Исключено» пустые; перекачайте "
                          "реестр свежей версией (москва_стройка.py нострой --заново)")),
        ("Регион СРО", "субъект, где зарегистрировано больше всего её действующих членов"),
        ("Посчитано", f"{сегодня:%d.%m.%Y}, статистика_сро.py"),
    ]
    out = Path(args.out)
    записать(out, строки, годы, список_месяцев, сведения, даты_исключения, покрытие)
    действующих = sum(s["действующих"] for s in строки)
    print(f"[сро] СРО: {len(строки)}; записей: {len(все)} (полнота {доля}); "
          f"действующих членств: {действующих} → {out}")
    if заявлено and len(все) < заявлено * 0.99:
        print("[сро] ВНИМАНИЕ: выгрузка неполная (меньше 99 % заявленного) — цифры занижены. "
              "Повторите: python москва_стройка.py нострой", file=sys.stderr)
    if args.с_членами:
        out2 = out.with_name(out.stem + "_члены.xlsx")
        записать_членов(out2, строки, поле)
        print(f"[сро] списки членов по СРО → {out2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
