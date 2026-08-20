#!/usr/bin/env python3
"""
Пересобирает адреса в кэше, НЕ обращаясь к checko.ru.

Карточки, полученные до исправления разбора, хранят в поле ``addresses`` весь
список: юридический адрес, адреса подразделений и адрес самой СРО. Скрипт
оставляет в каждой карточке один — юридический, — не тратя ни одного запроса
и не трогая суточную квоту. Уже пробитые компании остаются пробитыми.

    python3 rebuild_addresses.py --state output/state/checko_state.json --dry-run
    python3 rebuild_addresses.py --state output/state/checko_state.json

После этого достаточно обычного запуска main.py: отчёт пересоберётся из кэша.

Исходный список адресов сохраняется в ``extra.addresses_all``, поэтому скрипт
можно запускать повторно — выбор каждый раз делается заново из полного набора,
а не из уже усечённого.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nostroy_checko.address_pick import (
    ORIGINAL_KEY,
    detect_shared_addresses,
    full_address_list,
    rebuild_card,
)


def load_state(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Файл состояния не найден: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Файл состояния повреждён: {error}")


def original_addresses(card: dict) -> list[str]:
    """Полный список адресов карточки — из extra, если пересборка уже была."""
    return full_address_list(card.get("addresses"), card.get("extra"))


def rebuild(state: dict) -> tuple[list[dict], set[str]]:
    """Пересобирает адреса. Возвращает (изменения, найденные адреса СРО)."""
    results = state.get("results") or {}
    shared = detect_shared_addresses(original_addresses(card) for card in results.values())

    changes: list[dict] = []
    for key, card in results.items():
        full = original_addresses(card)
        if not full:
            continue

        inn = str(card.get("inn") or key)
        addresses, extra, ambiguous, empty = rebuild_card(
            card.get("addresses"), card.get("extra"), inn, shared
        )
        chosen = addresses[0] if addresses else ""

        before = "; ".join(card.get("addresses") or [])
        if before != chosen:
            changes.append(
                {
                    "key": key,
                    "name": card.get("name") or "",
                    "before": before,
                    "after": chosen,
                    "ambiguous": ambiguous and not empty,
                    "empty": empty,
                }
            )

        card["extra"] = extra
        card["addresses"] = addresses

    return changes, shared


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--state",
        default="output/state/checko_state.json",
        help="файл состояния (по умолчанию output/state/checko_state.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="показать изменения, ничего не записывая")
    parser.add_argument("--limit", type=int, default=20, help="сколько изменений печатать")
    args = parser.parse_args()

    path = Path(args.state)
    state = load_state(path)
    total = len(state.get("results") or {})
    changes, shared = rebuild(state)

    if shared:
        print(f"Определены адреса СРО ({len(shared)}) — они исключены из карточек:")
        for address in sorted(shared):
            print(f"   - {address}")
        print()

    print(f"Карточек в кэше: {total}")
    print(f"Адрес изменится: {len(changes)}")
    ambiguous = [item for item in changes if item["ambiguous"]]
    empty = [item for item in changes if item["empty"]]
    if ambiguous:
        print(f"Из них выбор неоднозначен: {len(ambiguous)} — стоит уточнить в checko.ru")
    if empty:
        print(f"Собственного адреса в карточке нет: {len(empty)} — были только адреса СРО")
    print()

    for item in changes[: args.limit]:
        if item["empty"]:
            mark = "  [АДРЕСА НЕТ]"
        elif item["ambiguous"]:
            mark = "  [НЕОДНОЗНАЧНО]"
        else:
            mark = ""
        print(f"  {item['name'][:52] or item['key']}{mark}")
        print(f"      было:  {item['before'][:150]}")
        print(f"      стало: {item['after'][:150] or '—'}")
    if len(changes) > args.limit:
        print(f"  … и ещё {len(changes) - args.limit}")

    if args.dry_run:
        print("\n--dry-run: файл не изменён.")
        return

    if not changes:
        print("Менять нечего — адреса уже пересобраны.")
        return

    backup = path.with_suffix(path.suffix + ".before-rebuild")
    shutil.copy2(path, backup)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)

    print(f"\nЗаписано: {path}")
    print(f"Резервная копия: {backup}")
    print("Квота не тронута — запросов к checko.ru не было.")
    print("Дальше: обычный запуск main.py — отчёт пересоберётся из кэша.")


if __name__ == "__main__":
    main()
