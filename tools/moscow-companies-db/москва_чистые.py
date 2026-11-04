"""Москва: «чистые» строительные компании — новые, не из прежних списков, без СРО.

Нужны действующие юрлица с основным ОКВЭД 41/42/43 и юридическим адресом
в Москве, которые никогда не состояли в строительном СРО и не попадали
в прежнюю работу (очередь москва_для_checko.xlsx). Источник — своя база
mosstroybase.sqlite3 (реестр МСП ФНС: Москва, строительный ОКВЭД, без
ликвидированных).

ПОРЯДОК (из папки со скриптами, база лежит там же):

    python москва_чистые.py кандидаты
    python москва_чистые.py нострой
    python checko_контакты.py --file москва_чистые.xlsx --key КЛЮЧ
    python отбор_стройка.py --file москва_чистые.xlsx --out москва_чистые_итог.xlsx

«кандидаты» берёт из базы 120 компаний (--n), которых нет в прежних списках
(--исключить, по умолчанию москва_для_checko.xlsx). Сначала средние и малые,
потом микро — те, что в реестре МСП больше года; внутри группы — вразброс.

«нострой» проверяет их по реестру НОСТРОЙ — это бесплатно. Кто состоит или
состоял в строительном СРО, получает «Не пробивать», и Checko на них лимит
не тратит. Как только набралось 75 никогда не состоявших (--хватит),
остальных проверка не трогает и помечает запасом — чтобы Checko уложился
в суточный лимит. Повторный запуск с бо́льшим --хватит берёт запас в работу.

Checko даёт свежий статус, адрес, ОКВЭД и телефоны, отбор_стройка.py
раскладывает итог: лист «Подходят» — то, что нужно.
"""

from __future__ import annotations

import argparse
import importlib.util
import random
import re
import sqlite3
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

_ЗДЕСЬ = Path(__file__).resolve().parent


def _модуль(имя: str, файл: str):
    spec = importlib.util.spec_from_file_location(имя, _ЗДЕСЬ / файл)
    модуль = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(модуль)
    return модуль


checko = _модуль("checko_контакты", "checko_контакты.py")

ФАЙЛ = "москва_чистые.xlsx"
ПРЕЖНИЕ = "москва_для_checko.xlsx"
СТРОЙКА = ("41", "42", "43")
В_НОСТРОЙ = "В НОСТРОЙ"
СРО_НОСТРОЙ = "Строительное СРО (НОСТРОЙ)"
ЗАПАС = "запас: по НОСТРОЙ не проверялась — хватило других"
НЕ_ОТВЕТИЛ = "НОСТРОЙ не ответил — повторите «нострой» перед Checko"
КОЛОНКИ = ["Наименование", "ИНН", checko.НЕ_ПРОБИВАТЬ, В_НОСТРОЙ, СРО_НОСТРОЙ,
           "ОКВЭД основной (база МСП)", "Категория МСП", "В реестре МСП с", "Адрес (база МСП)"]
_ПОРЯДОК_КАТЕГОРИЙ = {"среднее": 0, "малое": 1, "микро": 2}


def инн_верный(инн: str) -> bool:
    """ИНН юрлица: 10 цифр и сходится контрольная цифра."""
    if not re.fullmatch(r"\d{10}", инн or ""):
        return False
    веса = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    return sum(int(ц) * в for ц, в in zip(инн, веса)) % 11 % 10 == int(инн[9])


def прежние_инн(файлы: list[str]) -> tuple[set[str], list[str]]:
    """ИНН из прежних списков; второй элемент — каких файлов не нашлось."""
    инн, нет = set(), []
    for имя in файлы:
        путь = Path(имя)
        if not путь.exists():
            нет.append(имя)
            continue
        _шапка, строки = checko.read_rows(путь)
        for r in строки:
            цифры = re.sub(r"\D", "", r.get("ИНН") or "")
            if цифры:
                инн.add(цифры.zfill(10) if len(цифры) == 9 else цифры)
    return инн, нет


def из_базы(путь: Path) -> list[dict]:
    """Юрлица Москвы с основным ОКВЭД 41/42/43 из базы реестра МСП."""
    con = sqlite3.connect(f"file:{путь}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        строки = [dict(r) for r in con.execute(
            "SELECT inn, name, name_short, kind, region_code, address, okved_main, "
            "msp_category, msp_since, is_active, egrul_status, sro_member FROM companies "
            "WHERE region_code = '77' AND (okved_main LIKE '41%' OR okved_main LIKE '42%' "
            "OR okved_main LIKE '43%')")]
    finally:
        con.close()
    return строки


def годится(r: dict, исключить: set[str]) -> bool:
    if (r.get("kind") or "ЮЛ") != "ЮЛ" or not инн_верный(r.get("inn") or ""):
        return False
    if r["inn"] in исключить or not (r.get("okved_main") or "").startswith(СТРОЙКА):
        return False
    статус = (r.get("egrul_status") or "").lower()
    if r.get("is_active") == 0 or any(с in статус for с in ("ликвид", "прекращ", "исключ", "банкрот")):
        return False
    return r.get("sro_member") != 1


def порядок(r: dict, сегодня: date) -> tuple[int, int]:
    """Средние и малые раньше микро; среди микро — те, что в реестре МСП больше года."""
    категория = _ПОРЯДОК_КАТЕГОРИЙ.get((r.get("msp_category") or "").strip().lower(), 3)
    с = r.get("msp_since") or ""
    молодая = 1 if (not с or с > (сегодня - timedelta(days=365)).isoformat()) else 0
    return категория, молодая


def отобрать(строки: list[dict], исключить: set[str], n: int, зерно: int,
             сегодня: date | None = None) -> list[dict]:
    сегодня = сегодня or date.today()
    подходящие = [r for r in строки if годится(r, исключить)]
    random.Random(зерно).shuffle(подходящие)        # вразброс внутри группы
    подходящие.sort(key=lambda r: порядок(r, сегодня))
    return подходящие[:n]


def cmd_кандидаты(args) -> int:
    база, out = Path(args.база), Path(args.out)
    if not база.exists():
        print(f"Нет базы {база}. Она должна лежать в папке со скриптами (или --база <путь>).",
              file=sys.stderr)
        return 1
    if out.exists() and not args.заново:
        print(f"{out} уже есть — в нём может быть прогресс. Новый список: --заново "
              f"(старый файл будет перезаписан) или другое имя: --out", file=sys.stderr)
        return 1
    исключить, нет = прежние_инн(args.исключить)
    for имя in нет:
        print(f"[чистые] ВНИМАНИЕ: файла {имя} нет — компании из него не исключены", file=sys.stderr)
    строки = из_базы(база)
    выбор = отобрать(строки, исключить, args.n, args.зерно)
    if not выбор:
        print("[чистые] в базе не нашлось ни одной подходящей компании", file=sys.stderr)
        return 1
    записи = [{"Наименование": r.get("name_short") or r.get("name") or "", "ИНН": r["inn"],
               "ОКВЭД основной (база МСП)": r.get("okved_main") or "",
               "Категория МСП": r.get("msp_category") or "",
               "В реестре МСП с": r.get("msp_since") or "",
               "Адрес (база МСП)": r.get("address") or ""} for r in выбор]
    checko.write_rows(out, КОЛОНКИ, записи)
    категории = Counter(r.get("msp_category") or "не указана" for r in выбор)
    print(f"[чистые] в базе Москва + ОКВЭД 41–43: {len(строки)}; исключено как прежние: "
          f"{sum(1 for r in строки if r['inn'] in исключить)}")
    print(f"[чистые] взято {len(выбор)}: " + ", ".join(f"{к} {в}" for к, в in категории.most_common()))
    print(f"[чистые] записано в {out}. Дальше: python москва_чистые.py нострой")
    return 0


# -- проверка по НОСТРОЙ ------------------------------------------------


def вердикт(payload, инн: str, нострой) -> tuple[str, str]:
    """(«состоит» / «была» / «не состояла» / «разобрать вручную», подпись СРО)."""
    свои = [r for r in нострой.records_of(payload) if нострой.норм_инн(r.get("inn")) == инн]
    действующее, прекращённое = нострой.членства_строителя(payload, инн)
    if действующее:
        return "состоит", f"{действующее[1]} ({действующее[2]})".replace(" ()", "")
    if прекращённое:
        return "была", f"вышла из: {прекращённое[1]}"
    if свои:
        # запись есть, но без даты вступления — не гадаем, это не «чистая»
        return "разобрать вручную", "в реестре есть запись, статус не разобрался"
    return "не состояла", ""


def cmd_нострой(args) -> int:
    путь = Path(args.file)
    if not путь.exists():
        print(f"Нет файла {путь}. Сначала: python москва_чистые.py кандидаты", file=sys.stderr)
        return 1
    нострой = _модуль("выгрузка_ностроя", "выгрузка_ностроя.py")
    шапка, строки = checko.read_rows(путь)
    for колонка in (checko.НЕ_ПРОБИВАТЬ, В_НОСТРОЙ, СРО_НОСТРОЙ):
        if колонка not in шапка:
            шапка.insert(шапка.index("ИНН") + 1 if колонка == checko.НЕ_ПРОБИВАТЬ else len(шапка), колонка)
    for r in строки:          # запас и неответившие прошлого запуска — снова в работу
        if (r.get(checko.НЕ_ПРОБИВАТЬ) or "") in (ЗАПАС, НЕ_ОТВЕТИЛ) and not r.get(В_НОСТРОЙ):
            r[checko.НЕ_ПРОБИВАТЬ] = ""

    def чистых() -> int:
        return sum(1 for r in строки if r.get(В_НОСТРОЙ) == "не состояла")

    очередь = [r for r in строки if not r.get(В_НОСТРОЙ) and инн_верный(r.get("ИНН") or "")]
    print(f"[чистые] к проверке по НОСТРОЙ: {len(очередь)}; уже никогда не состоявших: {чистых()}. "
          f"Каждая компания — строка ниже; первый ответ реестра бывает через несколько секунд",
          flush=True)
    session = нострой.make_session()
    осечки = 0
    try:
        for номер, r in enumerate(очередь, 1):
            if чистых() >= args.хватит:
                break
            инн = r["ИНН"]
            payload = нострой.fetch_by_inn(session, инн)
            if payload is None:
                # без проверки в Checko не пускаем: лимит ушёл бы, а СРО осталось бы неизвестным
                r[checko.НЕ_ПРОБИВАТЬ] = НЕ_ОТВЕТИЛ
                осечки += 1
                print(f"[чистые] ИНН {инн}: реестр не ответил — спрошу при следующем запуске",
                      file=sys.stderr)
                continue
            итог, подпись = вердикт(payload, инн, нострой)
            r[В_НОСТРОЙ], r[СРО_НОСТРОЙ] = итог, подпись
            if итог != "не состояла":
                r[checko.НЕ_ПРОБИВАТЬ] = {"состоит": "состоит в строительном СРО (НОСТРОЙ)",
                                          "была": "была в строительном СРО (НОСТРОЙ)"}.get(
                    итог, "НОСТРОЙ: запись есть, статус не разобрался")
            print(f"[чистые] {номер}/{len(очередь)} {инн}: {итог}"
                  f" — никогда не состоявших {чистых()} из {args.хватит}", flush=True)
            if номер % 10 == 0:
                checko.write_rows(путь, шапка, строки)
            time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\n[чистые] прервано — сохраняю; та же команда продолжит с места остановки")
    запас = 0
    if чистых() >= args.хватит:
        for r in строки:
            if not r.get(В_НОСТРОЙ) and not (r.get(checko.НЕ_ПРОБИВАТЬ) or ""):
                r[checko.НЕ_ПРОБИВАТЬ] = ЗАПАС
                запас += 1
    checko.write_rows(путь, шапка, строки)
    итоги = Counter(r.get(В_НОСТРОЙ) or "не проверена" for r in строки)
    print("[чистые] итог: " + ", ".join(f"{к} — {в}" for к, в in итоги.most_common()))
    if запас:
        print(f"[чистые] набралось {args.хватит} никогда не состоявших; ещё {запас} отложены запасом")
    if осечки:
        print(f"[чистые] ВНИМАНИЕ: {осечки} ИНН реестр не отдал — запустите команду ещё раз",
              file=sys.stderr)
    к_checko = len(checko.осталось_пробить(строки))
    print(f"[чистые] в Checko пойдут {к_checko}: python checko_контакты.py --file {путь} --key КЛЮЧ")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Чистые строительные компании Москвы без СРО")
    sub = p.add_subparsers(dest="команда")
    k = sub.add_parser("кандидаты", help="взять компании из базы МСП")
    k.add_argument("--база", default="mosstroybase.sqlite3")
    k.add_argument("--out", default=ФАЙЛ)
    k.add_argument("--n", type=int, default=120, help="сколько взять (по умолчанию 120)")
    k.add_argument("--исключить", nargs="*", default=[ПРЕЖНИЕ],
                   help="файлы прежних списков с колонкой ИНН")
    k.add_argument("--зерно", type=int, default=2026, help="для разброса внутри групп")
    k.add_argument("--заново", action="store_true", help="перезаписать существующий файл")
    k.set_defaults(func=cmd_кандидаты)
    н = sub.add_parser("нострой", help="проверить по реестру НОСТРОЙ")
    н.add_argument("--file", default=ФАЙЛ)
    н.add_argument("--хватит", type=int, default=75,
                   help="сколько никогда не состоявших достаточно (по умолчанию 75)")
    н.add_argument("--delay", type=float, default=0.4, help="пауза между ИНН, сек")
    н.set_defaults(func=cmd_нострой)
    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
