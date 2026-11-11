"""Таблица по строительным СРО города из сводки НОСТРОЙ — в том же виде, что петербургская.

Сводку собирает сро_регион.py (папки spb_2026_11/, msk_2026_11/). Здесь из неё
получается xlsx: «Сводная» (всего, действующих, исключённых, вступило и исключено
по годам, руководитель), строка «Итого», листы «Вступления по месяцам» и
«Исключения по месяцам».

СРО, которые реестр НОСТРОЙ помечает недействующими (state «disabled» — исключены
из госреестра; в Москве их 45 из 101), в таблицу не включаются (решение заказчика
11.11.2026: только действующие): их «действующие» члены только числятся (у АС «РСА» —
4 872) и завысили бы цифры. Их число — пометкой под «Сводной». В файл для Checko
они тоже не попадают.

Руководителей в реестре НОСТРОЙ нет, их дают ЕГРЮЛ через Checko по ИНН СРО:

  python сро_таблица.py для-checko --сводка msk_2026_11/сводка.json --out мск_сро_руководители.xlsx
  python checko_контакты.py --file мск_сро_руководители.xlsx --key ВАШ_КЛЮЧ
  python сро_таблица.py таблица --сводка msk_2026_11/сводка.json --out MSK_SRO.xlsx \\
         --руководители мск_сро_руководители.xlsx
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import openpyxl
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.properties import CalcProperties

ГОДЫ = (2023, 2024, 2025, 2026)
ШАПКА = (["Рег. номер", "СРО", "Всего записей", "Действующих", "Исключённых (всего)"]
         + [f"Вступило {г}" for г in ГОДЫ] + ["Вступило 2023–2026"]
         + [f"Исключено {г}" for г in ГОДЫ] + ["Исключено 2023–2026", "Без даты искл.", "Руководитель"])
СИНИЙ = PatternFill("solid", fgColor="1F4E79")
ИТОГ = PatternFill("solid", fgColor="DDEBF7")
ТОНКАЯ = Side(style="thin", color="BFBFBF")
РАМКА = Border(left=ТОНКАЯ, right=ТОНКАЯ, top=ТОНКАЯ, bottom=ТОНКАЯ)


def короткое(название: str | None) -> str:
    """«СРО А «Объединение строителей СПб»» → «Объединение строителей СПб»."""
    s = (название or "").strip()
    if "«" in s and s.endswith("»"):
        s = s[s.index("«") + 1:-1].strip()
        s += "»" * (s.count("«") - s.count("»"))
    return s


def действует(x: dict) -> bool:
    return (x.get("карточка") or {}).get("состояние") in (None, "", "enabled")


def прочитать(путь: Path) -> dict:
    d = json.loads(путь.read_text(encoding="utf-8"))
    плохие = [x["рег_номер"] for x in d["сро"] if x.get("id") and x.get("полнота") != "полно"]
    if плохие:
        print(f"ВНИМАНИЕ: списки членов неполные у {', '.join(плохие)}", file=sys.stderr)
    return d


def руководители(путь: Path | None, сро: list[dict]) -> dict[str, str]:
    """Рег. номер → «ФИО, должность» из файла Checko (ИНН сверяется со сводкой)."""
    if not путь:
        return {}
    ws = openpyxl.load_workbook(путь, read_only=True).active
    строки = ws.iter_rows(values_only=True)
    шапка = [str(h or "").strip() for h in next(строки)]
    инн_по_номеру = {x["рег_номер"]: str(x.get("инн") or "") for x in сро}
    out = {}
    for r in строки:
        z = dict(zip(шапка, r))
        номер = str(z.get("Рег. номер") or "").strip()
        фио = str(z.get("Руководитель") or "").strip()
        if not номер or not фио:
            continue
        if str(z.get("ИНН") or "").strip() != инн_по_номеру.get(номер):
            print(f"{номер}: ИНН в файле руководителей не совпал со сводкой — пропускаю", file=sys.stderr)
            continue
        должность = str(z.get("Должность") or "").strip()
        out[номер] = f"{фио}, {должность[:1].lower() + должность[1:]}" if должность else фио
    return out


def cmd_для_checko(a) -> int:
    d = прочитать(Path(a.сводка))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Компании"
    ws.append(["Наименование", "ИНН", "Рег. номер"])
    for x in sorted(d["сро"], key=lambda x: x["рег_номер"]):
        if x.get("инн") and (a.все or действует(x)):
            ws.append([x.get("краткое_название"), str(x["инн"]), x["рег_номер"]])
    wb.save(a.out)
    print(f"{ws.max_row - 1} СРО → {a.out}")
    return 0


def _шапка_листа(ws, ширины: dict[str, float]) -> None:
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = СИНИЙ
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 28.8
    for к, ш in ширины.items():
        ws.column_dimensions[к].width = ш
    ws.freeze_panes = "C2"


def лист_сводки(ws, сро: list[dict], рук: dict[str, str], пометка: str) -> int:
    """Таблица как «Сводная» у Петербурга; возвращает номер последней строки СРО."""
    ws.append(ШАПКА)
    for x in сро:
        вступ = [x[f"вступило_{г}"] for г in ГОДЫ]
        искл = [x[f"исключено_{г}"] for г in ГОДЫ]
        ws.append([x["рег_номер"], короткое(x.get("краткое_название")), x["всего_записей"],
                   x["действующих"], x["исключённых_всего"], *вступ, sum(вступ), *искл, sum(искл),
                   x["без_даты_искл"], рук.get(x["рег_номер"], "")])
    n = len(сро) + 1
    for row in ws.iter_rows(min_row=2, max_row=n):
        for c in row:
            c.border = РАМКА
        row[-1].alignment = Alignment(wrap_text=True, vertical="top")
    ws.append(["", f"Итого по {len(сро)} СРО"]
              + [f"=SUM({L(j)}2:{L(j)}{n})" for j in range(3, len(ШАПКА))] + [""])
    for c in ws[n + 1][1:len(ШАПКА) - 1]:
        c.font = Font(bold=True)
        c.fill = ИТОГ
    for i, текст in enumerate(пометка.split("\n")):
        ws.cell(n + 3 + i, 1, текст).font = Font(italic=True, color="595959")
    _шапка_листа(ws, {"A": 20, "B": 42, **{L(j): 11 for j in range(3, len(ШАПКА))},
                      L(len(ШАПКА)): 44})
    ws.auto_filter.ref = f"A1:{L(len(ШАПКА))}{n}"
    return n


def cmd_таблица(a) -> int:
    d = прочитать(Path(a.сводка))
    все = sorted((x for x in d["сро"] if x.get("id")), key=lambda x: x["рег_номер"])
    сро = [x for x in все if действует(x)]
    не_действуют = [x for x in все if not действует(x)]
    рук = руководители(Path(a.руководители) if a.руководители else None, все)
    дата = d["дата_сбора"]
    дата_рус = f"{дата[8:10]}.{дата[5:7]}.{дата[:4]}"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Сводная"
    пометка = (f"Цифры на {дата_рус} по реестру НОСТРОЙ (списки членов и выгрузки реестров СРО). "
               "Запись = членство: компания, вступившая повторно, считается дважды.")
    if рук:
        пометка += " Руководители — ЕГРЮЛ (Checko) по ИНН СРО из реестра НОСТРОЙ."
    неполные = [f"{x['рег_номер']} ({x['получено']} из {x['заявлено_реестром']})"
                for x in все if x.get("полнота") != "полно"]
    if неполные:
        пометка += ("\nРеестр заявляет на запись больше, чем отдаёт, у " + ", ".join(неполные)
                    + " — повторный сбор даёт то же.")
    if не_действуют:
        пометка += (f"\nЕщё {len(не_действуют)} СРО города реестр помечает недействующими — "
                    "в таблицу они не включены.")
    n = лист_сводки(ws, сро, рук, пометка)

    месяцы = sorted(сро[0]["вступления_по_месяцам"])
    for i, (имя, ключ) in enumerate((("Вступления по месяцам", "вступления_по_месяцам"),
                                      ("Исключения по месяцам", "исключения_по_месяцам")), 1):
        w = wb.create_sheet(имя, i)
        w.append(["Рег. номер", "СРО"] + месяцы)
        for x in сро:
            w.append([x["рег_номер"], короткое(x.get("краткое_название"))]
                     + [x[ключ].get(м, 0) for м in месяцы])
        w.append(["", "Итого"] + [f"=SUM({L(j)}2:{L(j)}{n})" for j in range(3, len(месяцы) + 3)])
        for c in w[n + 1]:
            c.font = Font(bold=True)
        _шапка_листа(w, {"A": 20, "B": 40, **{L(j): 8 for j in range(3, len(месяцы) + 3)}})
        w.conditional_formatting.add(
            f"C2:{L(len(месяцы) + 2)}{n}",
            ColorScaleRule(start_type="num", start_value=0, start_color="FFFFFF",
                           end_type="max", end_color="5598E7"))
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    wb.save(a.out)
    print(f"{len(сро)} СРО, руководителей {len(рук)} → {a.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("для-checko", help="файл с ИНН СРО для checko_контакты.py")
    p.add_argument("--сводка", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--все", action="store_true", help="и недействующие СРО тоже")
    p.set_defaults(fn=cmd_для_checko)
    p = sub.add_parser("таблица", help="xlsx как у Петербурга")
    p.add_argument("--сводка", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--руководители", help="файл после checko_контакты.py")
    p.set_defaults(fn=cmd_таблица)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
