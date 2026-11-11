"""Юрлица Петербурга: торговля и услуги, где работают в основном женщины, 5–20 сотрудников.

Задача 10.11.2026: действующие юрлица СПб со штатом 5–20 человек, с налогами,
ОКВЭД — торговля и услуги, не производство; сотрудники в основном женщины.

Пола сотрудников нет ни в одном открытом источнике, поэтому отбор идёт по
отраслям, где по данным Росстата заняты в основном женщины: розница одеждой,
косметикой, аптеки, салоны красоты, образование, бухгалтерия,
агентства недвижимости, турагентства, клининг и т. п. (ГРУППЫ ниже). С того же
дня по просьбе заказчика — и лёгкое производство с женским штатом: пошив,
текстиль, пекарни и кондитерские, косметика (направления «Производство: …»);
медицину и стоматологию (86.2x, 86.90) заказчик тогда же снял.
Берётся только ОСНОВНОЙ ОКВЭД: по дополнительным в отбор попали бы и заводы.

Шаг 1 — кандидаты из выгрузки реестра МСП ФНС (data/rsmp.zip, та же, что для
базы Москвы). ЮЛ, регион 78, основной ОКВЭД из ГРУПП, численность (ССЧР
в реестре) от 5 до 20. Если в выгрузке численности нет — берутся микро-
и малые, численность проверит Checko.

  python спб_юрлица.py кандидаты --rsmp data\\rsmp.zip --out спб_юрлица.xlsx
  python спб_юрлица.py кандидаты --rsmp data\\rsmp.zip --out спб_юрлица.xlsx --дописать
      (дописать новых в тот же файл: пробитое в Checko остаётся, непробитые
       перемешиваются заново вместе с новыми)

Шаг 2 — Checko (налоги, сотрудники, статус, недостоверность):

  python checko_контакты.py --file спб_юрлица.xlsx --key ВАШ_КЛЮЧ

Шаг 3 — итог: действует, 5–20 сотрудников по Checko, налоги больше нуля,
недостоверных сведений нет, Петербург, ОКВЭД из ГРУПП.

  python спб_юрлица.py итог --file спб_юрлица.xlsx --out СПб_юрлица_итог.xlsx
"""
from __future__ import annotations

import argparse
import importlib.util
import random
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

_ЗДЕСЬ = Path(__file__).resolve().parent
sys.path.insert(0, str(_ЗДЕСЬ))
from mosstroybase.sources import rsmp  # noqa: E402


def _модуль(имя: str, файл: str):
    spec = importlib.util.spec_from_file_location(имя, _ЗДЕСЬ / файл)
    модуль = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(модуль)
    return модуль


checko = _модуль("checko_контакты", "checko_контакты.py")

# Направление → префиксы основного ОКВЭД. Отрасли, где по данным Росстата
# («Женщины и мужчины России») заняты в основном женщины; производства нет.
ГРУППЫ: dict[str, tuple[str, ...]] = {
    "Розница: одежда, обувь, текстиль": ("47.51", "47.71", "47.72"),
    "Розница: аптеки, медтовары, оптика": ("47.73", "47.74"),
    "Розница: косметика и парфюмерия": ("47.75",),
    "Розница: цветы и товары для животных": ("47.76",),
    "Розница: книги, канцтовары, игрушки": ("47.61", "47.62", "47.65"),
    "Розница: ювелирные изделия и часы": ("47.77",),
    "Розница: хлеб и кондитерские изделия": ("47.24",),
    "Опт: одежда, косметика, лекарства": ("46.42", "46.45", "46.46"),
    "Салоны красоты, парикмахерские": ("96.02",),
    "SPA, массаж, солярии": ("96.04",),
    "Химчистки и прачечные": ("96.01",),
    "Ателье, ремонт одежды": ("95.29.1",),
    "Ветеринария": ("75.00",),
    "Детские сады, частные школы, кружки и курсы": ("85.1", "85.41"),
    "Присмотр за детьми, уход за пожилыми": ("87", "88"),
    "Бухгалтерия и аудит": ("69.20",),
    "Агентства недвижимости": ("68.31",),
    "Турагентства": ("79",),
    "Кадровые агентства": ("78",),
    "Переводы": ("74.30",),
    "Клининг, уборка помещений": ("81.21", "81.22"),
    "Офисные услуги, колл-центры": ("82.1", "82.20"),
    "Страховые агенты и брокеры": ("66.22",),
    "Гостиницы": ("55.10",),
    # лёгкое производство (добавлено 10.11.2026)
    "Производство: пошив одежды и трикотажа": ("14.1", "14.2", "14.3"),
    "Производство: шторы, постельное бельё, текстиль": ("13.92",),
    "Производство: хлеб и кондитерские изделия": ("10.71", "10.72", "10.82"),
    "Производство: косметика и парфюмерия": ("20.42",),
}
СПБ = "78"
КОЛОНКИ = ["Наименование", "ИНН", "Направление", "ОКВЭД основной", "Сотрудников (реестр МСП)",
           "Категория МСП", "В реестре МСП с"]
ИТОГ_КОЛОНКИ = ["Наименование", "ИНН", "Телефон", "Почта", "Направление", "ОКВЭД основной (Checko)",
                "Сотрудников (СЧР)", "Налоги уплачено, ₽", "Адрес (Checko)", "Руководитель", "Статус (Checko)"]
ШИРИНА = {"Наименование": 40, "ИНН": 13, "Телефон": 22, "Почта": 30, "Направление": 34,
          "ОКВЭД основной (Checko)": 34, "Сотрудников (СЧР)": 12, "Налоги уплачено, ₽": 16,
          "Адрес (Checko)": 50, "Руководитель": 34, "Статус (Checko)": 16, "Почему не подходит": 50}
ЛИСТЫ = ("Подходят", "Не подходят", "Не проверены")


def направление(код: str | None) -> str | None:
    код = (код or "").strip()
    for имя, префиксы in ГРУППЫ.items():
        if any(код.startswith(п) for п in префиксы):
            return имя
    return None


def _число(значение) -> float | None:
    текст = str(значение if значение is not None else "").strip().replace(",", ".").replace(" ", "")
    текст = текст.replace("\xa0", "")
    try:
        return float(текст) if текст else None
    except ValueError:
        return None


def документы(путь: Path):
    """Документы реестра МСП с численностью (ССЧР) и признаком новой компании."""
    def из_потока(поток):
        for _e, elem in ET.iterparse(поток, events=("end",)):
            if rsmp._local(elem.tag) == "Документ":
                doc = rsmp._parse_document(elem)
                if doc:
                    doc["ссчр"] = elem.get("ССЧР")
                    doc["новый"] = elem.get("ПризНовМСП") == "1"
                    yield doc
                elem.clear()

    if путь.suffix.lower() != ".zip":
        with open(путь, "rb") as fh:
            yield from из_потока(fh)
        return
    with zipfile.ZipFile(путь) as zf:
        имена = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        for i, имя in enumerate(имена, 1):
            if i % 200 == 0 or i == len(имена):
                print(f"  файлов реестра: {i}/{len(имена)}", flush=True)
            with zf.open(имя) as fh:
                yield from из_потока(fh)


def cmd_кандидаты(a) -> int:
    out = Path(a.out)
    if out.exists() and not (a.заново or a.дописать):
        print(f"{out} уже есть (в нём может быть прогресс Checko). Дописать новых — --дописать, "
              "начать с нуля — --заново.", file=sys.stderr)
        return 1
    путь = Path(a.rsmp)
    if not путь.exists():
        print(f"нет выгрузки {путь}. Скачать: python -m mosstroybase fetch-rsmp", file=sys.stderr)
        return 1
    счёт = Counter()
    с_числом, без_числа = [], []
    for doc in документы(путь):
        if doc.get("region_code") != a.регион or doc.get("kind") != "ЮЛ":
            continue
        счёт["юрлиц в регионе"] += 1
        группа = направление(doc.get("okved_main"))
        if not группа:
            continue
        счёт["нужный ОКВЭД"] += 1
        строка = {"Наименование": doc.get("name_short") or doc.get("name"), "ИНН": doc["inn"],
                  "Направление": группа, "ОКВЭД основной": doc.get("okved_main"),
                  "Категория МСП": doc.get("msp_category") or "",
                  "В реестре МСП с": doc.get("msp_since") or ""}
        ссчр = _число(doc.get("ссчр"))
        if ссчр is not None:
            счёт["есть численность"] += 1
            if a.от <= ссчр <= a.до:
                строка["Сотрудников (реестр МСП)"] = int(ссчр)
                с_числом.append(строка)
        elif doc.get("msp_category") in ("микро", "малое") and not doc.get("новый"):
            строка["Сотрудников (реестр МСП)"] = "нет в реестре"
            без_числа.append(строка)
    print(f"юрлиц в регионе {a.регион}: {счёт['юрлиц в регионе']}, с нужным ОКВЭД: {счёт['нужный ОКВЭД']}, "
          f"из них с численностью в реестре: {счёт['есть численность']}")
    # численность в выгрузке есть — берём только 5–20; нет совсем — микро и малые
    строки = с_числом if счёт["есть численность"] else без_числа
    if not счёт["есть численность"]:
        print("В выгрузке численности нет: взяты микро- и малые, сотрудников проверит Checko.")
    random.Random(a.зерно).shuffle(строки)
    if a.n:
        строки = строки[:a.n]
    колонки = КОЛОНКИ
    if a.дописать and out.exists():
        шапка, старые = checko.read_rows(out)
        известные = {r.get("ИНН") for r in старые}
        новые = [r for r in строки if r["ИНН"] not in известные]
        пробитые = [r for r in старые if checko.пробита(r)]
        # непробитые — перемешать вместе с новыми, чтобы Checko шёл по всем направлениям
        # непробитые с направлением, которое из списка сняли, — убрать
        снятые = [r for r in старые if not checko.пробита(r) and not направление(r.get("ОКВЭД основной"))]
        очередь = [r for r in старые if not checko.пробита(r) and направление(r.get("ОКВЭД основной"))] + новые
        random.Random(a.зерно).shuffle(очередь)
        колонки = шапка + [к for к in КОЛОНКИ if к not in шапка]
        print(f"в файле было {len(старые)} (пробито в Checko {len(пробитые)}), "
              f"убрано снятых направлений {len(снятые)}, добавлено новых {len(новые)}")
        строки = пробитые + очередь
    checko.write_rows(out, колонки, строки)
    по_группам = Counter(r.get("Направление") for r in строки)
    print(f"кандидатов: {len(строки)} → {out}")
    for имя, n in по_группам.most_common():
        print(f"  {n:6}  {имя}")
    return 0


def разобрать(r: dict, от: int, до: int) -> tuple[str, str]:
    """(лист, почему не подходит)."""
    статус = str(r.get("Статус (Checko)") or "").strip()
    if not статус:
        return "Не проверены", "ещё не пробита в Checko"
    if статус.startswith(("лимит", "HTTP", "сеть", "ответ не", "не найдено")):
        return "Не проверены", f"Checko: {статус}"
    недост = r.get(checko.НЕДОСТОВЕРНОСТЬ)
    if недост is None or not str(недост).strip():
        return "Не проверены", "недостоверность не проверена — перепробить"
    причины = []
    с = статус.lower()
    if re.search(r"ликвид|прекращ|исключ|не действ|банкрот|конкурсн|реорганиз|наблюдени", с):
        причины.append(f"статус: {статус}")
    if str(недост).strip().lower() != "нет" or "недостоверн" in с:
        причины.append(f"недостоверные сведения ({str(недост).strip()})")
    if str(r.get("Банкротство") or "").strip():
        причины.append("сообщения о банкротстве")
    сотр = _число(r.get("Сотрудников (СЧР)"))
    if сотр is None:
        причины.append("нет данных о сотрудниках")
    elif not (от <= сотр <= до):
        причины.append(f"сотрудников {int(сотр)}")
    налоги = _число(r.get("Налоги уплачено, ₽"))
    if not налоги:
        причины.append("налогов нет" if налоги == 0 else "нет данных о налогах")
    регион = str(r.get("Регион (Checko)") or "").lower()
    if регион and "санкт-петербург" not in регион and регион != СПБ:
        причины.append(f"регион: {r.get('Регион (Checko)')}")
    код = str(r.get("ОКВЭД основной (Checko)") or "").split()
    if код and not направление(код[0]):
        причины.append(f"ОКВЭД не из списка: {r.get('ОКВЭД основной (Checko)')}")
    return ("Не подходят", "; ".join(причины)) if причины else ("Подходят", "")


def _формат(телефон: str) -> str:
    ц = телефон[2:] if телефон.startswith("+7") else телефон
    return f"+7 ({ц[:3]}) {ц[3:6]}-{ц[6:8]}-{ц[8:10]}" if len(ц) == 10 else телефон


def контакты(r: dict) -> dict:
    """Телефоны и почта из ответа Checko — без повторов, телефон в виде +7 (812) 123-45-67."""
    телефоны: list[str] = []
    for источник in ("Телефоны (Checko)", "Телефон из почты"):
        for т in checko._phones_in(r.get(источник) or ""):
            if т not in телефоны:
                телефоны.append(т)
    почты: list[str] = []
    for м in checko._EMAIL_RE.finditer(r.get("E-mail (Checko)") or ""):
        if м.group(0).lower() not in почты:
            почты.append(м.group(0).lower())
    return {"Телефон": "; ".join(_формат(т) for т in телефоны), "Почта": "; ".join(почты)}


def cmd_итог(a) -> int:
    _шапка, строки = checko.read_rows(Path(a.file))
    по_листам: dict[str, list[dict]] = {л: [] for л in ЛИСТЫ}
    for r in строки:
        лист, почему = разобрать(r, a.от, a.до)
        по_листам[лист].append({**r, **контакты(r), "Почему не подходит": почему})
    по_листам["Подходят"].sort(key=lambda r: (r.get("Направление") or "", r.get("Наименование") or ""))
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    wb.remove(wb.active)
    for лист in ЛИСТЫ:
        колонки = ИТОГ_КОЛОНКИ + ([] if лист == "Подходят" else ["Почему не подходит"])
        ws = wb.create_sheet(f"{лист} ({len(по_листам[лист])})")
        ws.append(колонки)
        for r in по_листам[лист]:
            ws.append([r.get(к, "") for к in колонки])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E79")
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for i, к in enumerate(колонки, 1):
            ws.column_dimensions[get_column_letter(i)].width = ШИРИНА.get(к, 16)
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions
    wb.save(a.out)
    print(" · ".join(f"{л}: {len(по_листам[л])}" for л in ЛИСТЫ), f"→ {a.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("кандидаты", help="отбор из выгрузки реестра МСП")
    p.add_argument("--rsmp", default="data/rsmp.zip")
    p.add_argument("--out", default="спб_юрлица.xlsx")
    p.add_argument("--регион", default=СПБ)
    p.add_argument("--n", type=int, default=0, help="взять не больше N (0 — всех)")
    p.add_argument("--зерно", type=int, default=2026)
    p.add_argument("--заново", action="store_true", help="перезаписать файл")
    p.add_argument("--дописать", action="store_true",
                   help="дописать новых в существующий файл, пробитое в Checko не трогать")
    p.set_defaults(fn=cmd_кандидаты)
    p = sub.add_parser("итог", help="разбор после Checko")
    p.add_argument("--file", default="спб_юрлица.xlsx")
    p.add_argument("--out", default="СПб_юрлица_итог.xlsx")
    p.set_defaults(fn=cmd_итог)
    for p in sub.choices.values():
        p.add_argument("--от", type=int, default=5, help="сотрудников не меньше")
        p.add_argument("--до", type=int, default=20, help="сотрудников не больше")
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
