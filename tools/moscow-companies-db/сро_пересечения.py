"""Сколько членов СРО не состоят в проектных и в изыскательских СРО.

Просьба 15.11.2026: у каждой строительной СРО — сколько её действующих членов
не состоят ни в одной проектной СРО и сколько — ни в одной изыскательской;
у проектной — сколько не в изыскательских, у изыскательской — сколько не в
проектных.

Списки всех членов берутся целиком из реестров (POST sro/all/member/list
НОСТРОЙ и НОПРИЗ, постранично, в несколько потоков, с кэшем страниц), членство
сверяется по ИНН. Считаются только ДЕЙСТВУЮЩИЕ членства («Является членом»)
и с той, и с другой стороны: исключённый из проектной СРО в ней «не состоит».

В репозиторий идут только числа по каждой СРО (russia_2026_11/пересечения.json).
Списки членов с ИНН — персональные данные ИП, они остаются в кэше вне репозитория.

  python сро_пересечения.py --нострой russia_2026_11/нострой.json --ноприз russia_2026_11/ноприз.json \\
         --out russia_2026_11/пересечения.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_ЗДЕСЬ = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("сро_регион", _ЗДЕСЬ / "сро_регион.py")
регион = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(регион)


def вид(рег_номер: str) -> str:
    м = re.search(r"(?:^|-)([СПИCI])-", str(рег_номер or "").upper())
    return {"C": "С", "I": "И"}.get(м.group(1), м.group(1)) if м else "?"


def действует(z: dict) -> bool:
    return регион.СТАТУС_ДЕЙСТВ.lower() in str((z.get("member_status") or {}).get("title") or "").lower()


def инн(z: dict) -> str:
    return re.sub(r"\D", "", str(z.get("inn") or ""))


def сро_id(z: dict) -> str:
    s = z.get("sro")
    if isinstance(s, dict) and s.get("id") is not None:
        return str(s["id"])
    return str(z.get("sro_id") or "")


def все_члены(реестр: str, кэш: Path, потоков: int) -> list[dict]:
    """Все записи sro/all/member/list реестра; страницы кладутся в кэш (докачка при обрыве)."""
    регион.BASE = регион.РЕЕСТРЫ[реестр]
    кэш.mkdir(parents=True, exist_ok=True)
    первая = регион.post("sro/all/member/list", регион.тело(1))["data"]
    заявлено, страниц = int(первая["count"]), int(первая["countPages"])
    (кэш / "1.json").write_text(json.dumps(первая["data"], ensure_ascii=False), encoding="utf-8")

    def страница(n: int) -> int:
        путь = кэш / f"{n}.json"
        if not путь.exists():
            данные = регион.post("sro/all/member/list", регион.тело(n))["data"]["data"]
            путь.write_text(json.dumps(данные, ensure_ascii=False), encoding="utf-8")
        if n % 50 == 0:
            print(f"  {реестр}: страница {n}/{страниц}", flush=True)
        return n

    with ThreadPoolExecutor(max_workers=потоков) as pool:
        list(pool.map(страница, range(2, страниц + 1)))
    по_id = {}
    for n in range(1, страниц + 1):
        for z in json.loads((кэш / f"{n}.json").read_text(encoding="utf-8")):
            по_id[z["id"]] = z
    print(f"{реестр}: заявлено {заявлено}, получено {len(по_id)}", flush=True)
    if len(по_id) != заявлено:
        print(f"  ВНИМАНИЕ: {реестр} отдал {len(по_id)} уникальных из {заявлено} — страницы "
              f"пересекаются (нестабильная сортировка); берите по СРО (члены_по_сро)", file=sys.stderr)
    return list(по_id.values())


ЗА_РАЗ = 10000   # pageCount: самая большая СРО НОПРИЗ — ~6 тыс. членов, берётся одним ответом


def члены_по_сро(реестр: str, сро: list[dict], кэш: Path, потоков: int) -> list[dict]:
    """Все члены реестра — по каждой СРО одним запросом (sro/{id}/member/list, pageCount=ЗА_РАЗ).

    Зачем: у НОПРИЗ sro/all/member/list сортирует нестабильно (sortBy игнорируется), страницы
    пересекаются — 15.11.2026 из 214 531 строки уникальных было 137 584, остальное повторы,
    а 77 тыс. членов не попали ни на одну страницу. Одна страница на СРО этого лишена.
    """
    регион.BASE = регион.РЕЕСТРЫ[реестр]
    кэш.mkdir(parents=True, exist_ok=True)
    неполные = []

    def одна(x: dict) -> list[dict]:
        путь = кэш / f"sro_{x['id']}.json"
        if путь.exists():
            return json.loads(путь.read_text(encoding="utf-8"))
        тело = регион.тело(1)
        тело["pageCount"] = str(ЗА_РАЗ)
        д = регион.post(f"sro/{x['id']}/member/list", тело)["data"]
        записи = list({z["id"]: z for z in д["data"]}.values())
        if len(записи) != int(д["count"]):
            неполные.append((x.get("рег_номер"), len(записи), int(д["count"])))
            return записи                      # не кэшируем — перезапуск спросит заново
        путь.write_text(json.dumps(записи, ensure_ascii=False), encoding="utf-8")
        return записи

    with ThreadPoolExecutor(max_workers=потоков) as pool:
        части = list(pool.map(одна, [x for x in сро if x.get("id")]))
    по_id = {z["id"]: z for ч in части for z in ч}
    print(f"{реестр} (по СРО): СРО {len(части)}, записей {len(по_id)}", flush=True)
    for н, есть, надо in неполные:
        print(f"  ВНИМАНИЕ: {реестр} {н}: уникальных {есть} из {надо} — перезапустите", file=sys.stderr)
    return list(по_id.values())


def посчитать(члены_с: list[dict], члены_пи: list[dict], сро_с: list[dict], сро_пи: list[dict]) -> dict:
    """Числа по каждой СРО. сро_* — записи сводок (рег_номер, id)."""
    # id СРО у НОСТРОЙ и НОПРИЗ свои (id 1 есть в обоих) — справочники раздельные
    номер_с = {str(x["id"]): x["рег_номер"] for x in сро_с if x.get("id")}
    номер_пи = {str(x["id"]): x["рег_номер"] for x in сро_пи if x.get("id")}
    в_проекте, в_изысканиях = set(), set()
    for z in члены_пи:
        if not действует(z) or not инн(z):
            continue
        в = вид(номер_пи.get(сро_id(z), ""))
        (в_проекте if в == "П" else в_изысканиях if в == "И" else set()).add(инн(z))
    итог: dict[str, Counter] = defaultdict(Counter)
    без_сро = Counter()
    for z, справочник in [(z, номер_с) for z in члены_с] + [(z, номер_пи) for z in члены_пи]:
        if not действует(z):
            continue
        номер = справочник.get(сро_id(z))
        if not номер:
            без_сро[сро_id(z)] += 1
            continue
        и, к = инн(z), итог[номер]
        к["действующих"] += 1
        if not и:
            к["без_инн"] += 1
            continue
        к["не_в_проекте"] += и not in в_проекте
        к["не_в_изысканиях"] += и not in в_изысканиях
        к["ни_там_ни_там"] += и not in в_проекте and и not in в_изысканиях
    return {"сро": {н: dict(к) for н, к in sorted(итог.items())},
            "инн_в_проектных": len(в_проекте), "инн_в_изыскательских": len(в_изысканиях),
            "записей_без_сро_в_сводке": sum(без_сро.values())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--нострой", required=True, help="сводка сро_регион.py по НОСТРОЙ (для id ↔ рег. номер)")
    ap.add_argument("--ноприз", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--кэш", default=os.path.expanduser("~/.cache/сро_все_члены"))
    ap.add_argument("--потоков", type=int, default=4)
    a = ap.parse_args(argv)
    сро_с = json.loads(Path(a.нострой).read_text(encoding="utf-8"))["сро"]
    сро_пи = json.loads(Path(a.ноприз).read_text(encoding="utf-8"))["сро"]
    члены_с = все_члены("нострой", Path(a.кэш) / "нострой", a.потоков)
    # НОПРИЗ — только по СРО: общий список у него теряет треть членов (см. члены_по_сро)
    члены_пи = члены_по_сро("ноприз", сро_пи, Path(a.кэш) / "ноприз_по_сро", a.потоков)
    статусы = Counter(str((z.get("member_status") or {}).get("title")) for z in члены_с + члены_пи)
    итог = посчитать(члены_с, члены_пи, сро_с, сро_пи)
    итог.update({"дата_сбора": dt.date.today().isoformat(), "статусы": dict(статусы),
                 "пояснение": "действующие члены СРО; «не_в_проекте» — ИНН нет среди действующих членов "
                              "ни одной проектной СРО (НОПРИЗ, «-П-»), «не_в_изысканиях» — ни одной "
                              "изыскательской («-И-»); сверка по ИНН"})
    Path(a.out).write_text(json.dumps(итог, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"статусы: {dict(статусы)}")
    print(f"ИНН в проектных: {итог['инн_в_проектных']}, в изыскательских: {итог['инн_в_изыскательских']}, "
          f"СРО: {len(итог['сро'])}, записей без СРО в сводке: {итог['записей_без_сро_в_сводке']} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
