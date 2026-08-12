#!/usr/bin/env python3
"""Проверка членства компаний в СРО по реестрам НОСТРОЙ и НОПРИЗ.

Простой запуск:
    python check_sro.py --input Компании_Список.xlsx

Проверить, работает ли API реестров (полезно запустить первым делом):
    python check_sro.py --probe 7702521529

Перепроверить только те строки, где написано «не удалось проверить»:
    python check_sro.py --input Компании_Список_с_СРО.xlsx --retry-failed

Подробности — в README.md рядом с этим файлом.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

from sro import excel_io
from sro.excel_io import COL_VERDICT
from sro.inn import describe_problem, is_valid_inn, normalize_inn
from sro.models import (
    SOURCE_NOPRIZ,
    SOURCE_NOSTROY,
    CheckResult,
    Outcome,
    RegistryAnswer,
    Verdict,
)
from sro.registries import build_providers

DATE_FORMAT = "%d.%m.%Y %H:%M"


def _print_line(message: str) -> None:
    """Печать в консоль. У оконной сборки консоли нет — тогда просто молчим."""
    try:
        print(message, flush=True)
    except (OSError, ValueError, AttributeError):
        pass


# ---------------------------------------------------------------------------
# Вспомогательное
# ---------------------------------------------------------------------------


class Log:
    """Пишет в консоль (или в переданный приёмник) и в файл одновременно.

    `sink` позволяет графическому интерфейсу забирать строки себе в окно
    вместо консоли, которой у оконного приложения нет.
    """

    def __init__(self, path: str | None = None, sink=None) -> None:
        self.handle = open(path, "a", encoding="utf-8") if path else None
        self.sink = sink if sink is not None else _print_line

    def __call__(self, message: str = "") -> None:
        self.sink(message)
        if self.handle:
            self.handle.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")
            self.handle.flush()

    def close(self) -> None:
        if self.handle:
            self.handle.close()


def load_cache(path: str) -> dict[str, CheckResult]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError):
        return {}
    results: dict[str, CheckResult] = {}
    for inn, data in (raw.get("results") or {}).items():
        try:
            results[inn] = CheckResult.from_dict(data)
        except Exception:
            continue
    return results


def save_cache(path: str, cache: dict[str, CheckResult]) -> None:
    if not path:
        return
    payload = {
        "saved_at": datetime.now().strftime(DATE_FORMAT),
        "results": {inn: result.to_dict() for inn, result in cache.items()},
    }
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
    os.replace(temporary, path)


def save_workbook_atomic(workbook, path: str) -> str:
    """Сохранить книгу так, чтобы обрыв не испортил уже готовый файл.

    Если файл занят (например, открыт в Excel — обычное дело), сохраняем рядом
    под другим именем и возвращаем его: терять уже проверенное нельзя.
    Возвращает путь, по которому файл реально сохранён.
    """
    temporary = f"{path}.tmp"
    try:
        workbook.save(temporary)
        os.replace(temporary, path)
        return path
    except OSError:
        stem, extension = os.path.splitext(path)
        alternative = f"{stem}_{datetime.now():%Y%m%d_%H%M%S}{extension}"
        workbook.save(alternative)
        return alternative


def default_output(input_path: str) -> str:
    folder, filename = os.path.split(input_path)
    stem, extension = os.path.splitext(filename)
    stem = stem.replace("_с_СРО", "")
    return os.path.join(folder, f"{stem}_с_СРО{extension or '.xlsx'}")


# ---------------------------------------------------------------------------
# Проверка одной компании
# ---------------------------------------------------------------------------


def check_company(
    inn: str,
    priority: str,
    providers: dict,
    browser,
    browser_mode: str,
    check_all: bool,
    delay_min: float,
    delay_max: float,
    basis: str,
    log: Log,
    cancel=None,
) -> CheckResult:
    """Опросить реестры по одному ИНН."""
    result = CheckResult(inn=inn, checked_at=datetime.now().strftime(DATE_FORMAT), basis=basis)

    for source in excel_io.registry_order(priority):
        answer: RegistryAnswer | None = None

        if browser_mode != "always":
            answer = providers[source].lookup(inn)
            _pause(delay_min, delay_max, cancel)

        # Браузер подключаем, если прямой запрос не дал понятного ответа.
        needs_browser = browser_mode == "always" or (
            browser_mode == "auto" and (answer is None or answer.outcome is Outcome.UNKNOWN)
        )
        if needs_browser and browser is not None:
            browser_answer = browser.lookup(source, inn)
            _pause(delay_min, delay_max, cancel)
            if browser_answer.outcome is not Outcome.UNKNOWN or answer is None:
                answer = browser_answer

        if answer is None:
            answer = RegistryAnswer(source, Outcome.UNKNOWN, note="проверка не выполнялась")

        result.answers.append(answer)

        # Нашли — второй реестр обычно уже не нужен.
        if answer.outcome is Outcome.FOUND and not check_all:
            break

    return result


def _with_basis(result: CheckResult, basis: str) -> CheckResult:
    """Пересчитать вердикт по текущему правилу (кэш мог быть записан по другому)."""
    result.basis = basis
    return result


def _pause(delay_min: float, delay_max: float, cancel=None) -> None:
    """Пауза между обращениями к реестру: не нагружаем государственный сервис.

    Если передан `cancel` (threading.Event), пауза прерывается сразу по нажатию
    «Стоп» — иначе пользователь ждал бы окончания сна впустую.
    """
    if delay_max <= 0:
        return
    seconds = random.uniform(max(0.0, delay_min), max(delay_min, delay_max))
    if cancel is not None:
        cancel.wait(seconds)
    else:
        time.sleep(seconds)


# ---------------------------------------------------------------------------
# Режим диагностики
# ---------------------------------------------------------------------------


def run_probe(args, log: Log, cancel=None) -> int:
    inn = normalize_inn(args.probe)
    log(f"Диагностика API реестров по ИНН {inn}")
    if not is_valid_inn(inn):
        log(f"  ВНИМАНИЕ: {describe_problem(args.probe, inn)}")
    log("")

    providers = build_providers(
        timeout=args.timeout,
        attempts=1,
        logger=log,
        nostroy_url=args.nostroy_url,
        nopriz_url=args.nopriz_url,
    )

    any_working = False
    working_urls: dict[str, str] = {}
    for source, provider in providers.items():
        log(f"=== {source} ===")
        for row in provider.probe(inn):
            marker = {"found": "РАБОТАЕТ, найдено", "empty": "РАБОТАЕТ, не найдено"}.get(
                row["result"], "не подошёл"
            )
            log(f"  [{marker}] {row['endpoint']}  ({row['url']})")
            if row.get("note"):
                log(f"      {row['note']}")
            if row.get("found"):
                for membership in row["found"]:
                    log(
                        f"      СРО: {membership.get('sro_name')} | "
                        f"№ {membership.get('registry_number')} | {membership.get('status')}"
                    )
            if row["result"] in ("found", "empty"):
                any_working = True
                working_urls.setdefault(source, row["url"])
            elif row.get("sample"):
                log(f"      начало ответа: {row['sample'][:200]}")
            _pause(args.delay_min, args.delay_max, cancel)
        log("")
        if cancel is not None and cancel.is_set():
            log("Диагностика остановлена.")
            return 1

    if args.browser != "never":
        log("=== Проверка через браузер ===")
        try:
            from sro.browser import BrowserLookup

            with BrowserLookup(headless=not args.show_browser, logger=log) as browser:
                for source in (SOURCE_NOSTROY, SOURCE_NOPRIZ):
                    answer = browser.lookup(source, inn)
                    log(f"  {source}: {answer.outcome.value} {answer.note}")
                    if answer.outcome is not Outcome.UNKNOWN:
                        any_working = True
                if browser.discovered_urls:
                    log("")
                    log("  Найденные адреса API (можно передать в параметрах):")
                    for source, url in browser.discovered_urls.items():
                        flag = "--nostroy-url" if source == SOURCE_NOSTROY else "--nopriz-url"
                        log(f"    {flag} \"{url.split('?')[0]}\"")
        except Exception as error:
            log(f"  браузер недоступен: {error}")
        log("")

    if working_urls:
        log("Рабочие адреса — впишите их в программе, чтобы она больше не искала:")
        for source, url in working_urls.items():
            flag = "--nostroy-url" if source == SOURCE_NOSTROY else "--nopriz-url"
            log(f"    поле «Адрес API {source}»:  {url}")
            log(f'        (в командной строке: {flag} "{url}")')
        log("")

    if any_working:
        log("ИТОГ: рабочий способ проверки есть — можно запускать основную обработку.")
        return 0
    log("ИТОГ: ни один способ не сработал. Проверьте интернет/VPN или откройте сайты вручную.")
    return 1


# ---------------------------------------------------------------------------
# Основной проход
# ---------------------------------------------------------------------------


def run(args, log: Log, cancel=None, progress=None) -> int:
    """Основной проход по файлу.

    `cancel`   — threading.Event: взведённый останавливает работу так же
                 аккуратно, как Ctrl+C (всё проверенное сохраняется).
    `progress` — callback(processed, total, counters) для индикатора в окне.
    """
    if not os.path.exists(args.input):
        log(f"ОШИБКА: файл не найден: {args.input}")
        return 2

    workbook, worksheet, warnings = excel_io.open_sheet(args.input, args.sheet)
    for warning in warnings:
        log(f"ВНИМАНИЕ: {warning}")

    try:
        layout = excel_io.find_layout(worksheet)
    except ValueError as error:
        log(f"ОШИБКА: {error}")
        return 2

    log(f"Файл: {args.input}")
    log(f"Лист: «{worksheet.title}», строка заголовков: {layout.header_row}")

    added = excel_io.ensure_output_columns(worksheet, layout)
    if added:
        log("Добавлены колонки: " + ", ".join(added))
    if layout.columns.get(COL_VERDICT):
        letter = excel_io.get_column_letter(layout.columns[COL_VERDICT])
        log(f"Вердикт пишется в колонку {letter}")
    if "priority" not in layout.columns:
        log("ВНИМАНИЕ: колонка «Приоритет» не найдена — все компании проверяются сначала по НОСТРОЙ")

    companies = list(excel_io.iter_companies(worksheet, layout))
    if args.limit:
        companies = companies[: args.limit]
    if not companies:
        log("ОШИБКА: не нашёл ни одной строки с данными")
        return 2

    cache = load_cache(args.cache)
    if cache:
        log(f"Загружен кэш предыдущих проверок: {len(cache)} записей ({args.cache})")

    # Что считаем «уже проверенным»
    resolved_values = {Verdict.YES.value, Verdict.NO.value}

    plan: list[tuple] = []
    skipped_resolved = 0
    for row, raw_inn, name, priority in companies:
        inn = normalize_inn(raw_inn)
        cached = cache.get(inn) if inn else None
        sheet_verdict = excel_io.read_existing_verdict(worksheet, layout, row)

        already = (cached is not None and cached.verdict.value in resolved_values) or (
            sheet_verdict in resolved_values
        )
        if args.retry_failed and already:
            skipped_resolved += 1
            continue
        plan.append((row, raw_inn, inn, name, priority))

    total = len(plan)
    log(f"К проверке: {total} компаний" + (f" (пропущено уже проверенных: {skipped_resolved})" if skipped_resolved else ""))
    log(f"Пауза между запросами: {args.delay_min}–{args.delay_max} с")
    log("")

    providers = build_providers(
        timeout=args.timeout,
        attempts=args.attempts,
        logger=log,
        nostroy_url=args.nostroy_url,
        nopriz_url=args.nopriz_url,
    )

    browser = None
    browser_context = None
    if args.browser != "never":
        try:
            from sro.browser import BrowserLookup

            browser_context = BrowserLookup(headless=not args.show_browser, logger=log)
            browser = browser_context.__enter__()
            log("Браузерная проверка включена (запасной способ)")
        except Exception as error:
            log(f"ВНИМАНИЕ: браузер недоступен ({error}). Работаю только через API.")
            browser = None
            browser_context = None

    counters = {Verdict.YES: 0, Verdict.NO: 0, Verdict.UNKNOWN: 0}
    processed = 0
    from_cache = 0
    interrupted = False

    try:
        for row, raw_inn, inn, name, priority in plan:
            if cancel is not None and cancel.is_set():
                interrupted = True
                break
            processed += 1
            label = (name or "").strip()[:45] or f"строка {row}"

            problem = describe_problem(raw_inn, inn)
            if problem:
                # Плохой ИНН — это «не удалось проверить», а не «нет СРО».
                result = CheckResult(
                    inn=inn,
                    checked_at=datetime.now().strftime(DATE_FORMAT),
                    note=problem,
                    basis=args.verdict_basis,
                )
            elif (
                inn in cache
                and not args.recheck_all
                and _with_basis(cache[inn], args.verdict_basis).verdict is not Verdict.UNKNOWN
            ):
                result = _with_basis(cache[inn], args.verdict_basis)
                from_cache += 1
            else:
                try:
                    result = check_company(
                        inn=inn,
                        priority=priority,
                        providers=providers,
                        browser=browser,
                        browser_mode=args.browser,
                        check_all=args.check_all,
                        delay_min=args.delay_min,
                        delay_max=args.delay_max,
                        basis=args.verdict_basis,
                        log=log,
                        cancel=cancel,
                    )
                except KeyboardInterrupt:
                    raise
                except Exception as error:
                    # Непредвиденный сбой на одной компании не должен ронять
                    # весь прогон: помечаем строку и идём дальше.
                    result = CheckResult(
                        inn=inn,
                        checked_at=datetime.now().strftime(DATE_FORMAT),
                        note=f"сбой при проверке: {type(error).__name__}: {error}"[:200],
                        basis=args.verdict_basis,
                    )
                cache[inn] = result
                save_cache(args.cache, cache)

            excel_io.write_result(worksheet, layout, row, result, colorize=not args.no_color)
            counters[result.verdict] += 1

            if progress is not None:
                progress(
                    processed,
                    total,
                    {
                        "yes": counters[Verdict.YES],
                        "no": counters[Verdict.NO],
                        "unknown": counters[Verdict.UNKNOWN],
                    },
                )

            detail = result.sro_names or result.diagnostics or ""
            log(
                f"Проверено {processed} из {total} | {label} | ИНН {inn or '—'} → "
                f"{result.verdict.value}" + (f" | {detail[:70]}" if detail else "")
            )

            if processed % args.checkpoint_every == 0:
                try:
                    saved_to = save_workbook_atomic(workbook, args.output)
                except Exception as error:
                    # Не смогли сохранить — это не повод терять уже проверенное:
                    # всё лежит в кэше, продолжаем работу.
                    log(f"  … не удалось сохранить промежуточный файл ({error}); данные в кэше")
                else:
                    log(
                        f"  … промежуточный результат сохранён: {saved_to} "
                        f"(да: {counters[Verdict.YES]}, нет: {counters[Verdict.NO]}, "
                        f"не удалось: {counters[Verdict.UNKNOWN]})"
                    )

            # Ранняя защита от «тихой поломки»: если реестр отвечает, но
            # почему-то ни одна компания не найдена — вероятно, сломался разбор.
            if processed == 25 and counters[Verdict.YES] == 0 and counters[Verdict.NO] >= 20:
                log("")
                log("!" * 70)
                log("ВНИМАНИЕ: первые 25 компаний — все «нет». Это подозрительно.")
                log("Возможно, изменился формат ответа реестра и проверка идёт вхолостую.")
                log("Проверьте вручную: python check_sro.py --probe <ИНН компании, которая точно в СРО>")
                log("!" * 70)
                log("")

    except KeyboardInterrupt:
        interrupted = True
        log("")
        log("Остановлено пользователем — сохраняю то, что успел проверить…")
    else:
        if interrupted:
            log("")
            log("Остановлено — сохраняю то, что успел проверить…")
    finally:
        if browser_context is not None:
            try:
                browser_context.__exit__(None, None, None)
            except Exception:
                pass
        save_cache(args.cache, cache)

    # Финальное сохранение — уже вне finally, чтобы не «проглотить» возможную
    # ошибку из основного цикла.
    try:
        final_path = save_workbook_atomic(workbook, args.output)
    except Exception as error:
        log("")
        log(f"ОШИБКА СОХРАНЕНИЯ: {error}")
        log("Закройте файл, если он открыт в Excel, и запустите программу ещё раз —")
        log("проверенное сохранено в кэше, заново реестры опрашиваться не будут.")
        return 3
    if final_path != args.output:
        log("")
        log(f"ВНИМАНИЕ: файл {args.output} был занят, результат сохранён как {final_path}")

    log("")
    log("=" * 60)
    log(f"Готово. Результат: {final_path}")
    log(f"  да . . . . . . . . . . {counters[Verdict.YES]}")
    log(f"  нет  . . . . . . . . . {counters[Verdict.NO]}")
    log(f"  не удалось проверить   {counters[Verdict.UNKNOWN]}")
    if from_cache:
        log(f"  (из них взято из кэша: {from_cache})")

    if counters[Verdict.UNKNOWN]:
        log("")
        log("Чтобы перепроверить только непроверенные строки, запустите:")
        log(f'  python check_sro.py --input "{args.output}" --retry-failed')

    if counters[Verdict.YES] == 0 and counters[Verdict.NO] >= 20:
        log("")
        log("ВНИМАНИЕ: не найдено ни одной компании с СРО. Перед тем как верить этому")
        log("результату, проверьте работу реестров: python check_sro.py --probe <ИНН>")

    log("=" * 60)
    return 130 if interrupted else 0


# ---------------------------------------------------------------------------
# Разбор аргументов
# ---------------------------------------------------------------------------


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверка членства компаний в СРО (НОСТРОЙ и НОПРИЗ) по ИНН",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", default="Компании_Список.xlsx", help="исходный файл Excel")
    parser.add_argument("--sheet", default="Лиды по приоритету", help="название листа")
    parser.add_argument("--output", default="", help="файл результата (по умолчанию — рядом с исходным)")
    parser.add_argument("--cache", default="", help="файл кэша проверок (json)")
    parser.add_argument("--log", default="", help="файл журнала")

    parser.add_argument("--delay-min", type=float, default=1.0, help="минимальная пауза между запросами, с")
    parser.add_argument("--delay-max", type=float, default=2.0, help="максимальная пауза между запросами, с")
    parser.add_argument("--timeout", type=float, default=25.0, help="таймаут запроса, с")
    parser.add_argument("--attempts", type=int, default=3, help="попыток при сетевой ошибке")
    parser.add_argument("--checkpoint-every", type=int, default=20, help="как часто сохранять промежуточный файл")

    parser.add_argument("--limit", type=int, default=0, help="проверить только первые N строк (для пробы)")
    parser.add_argument("--retry-failed", action="store_true", help="только строки «не удалось проверить»")
    parser.add_argument("--recheck-all", action="store_true", help="игнорировать кэш и проверить всё заново")
    parser.add_argument("--check-all", action="store_true", help="опрашивать оба реестра, даже если уже нашли")
    parser.add_argument(
        "--verdict-basis",
        choices=("found", "active"),
        default="active",
        help=(
            "что считать ответом «да»: active — только действующее членство "
            "(исключён/приостановлено → «нет»); found — любая запись в реестре"
        ),
    )

    parser.add_argument(
        "--browser",
        choices=("never", "auto", "always"),
        default="auto",
        help="использовать браузер: never — никогда, auto — если API не ответил, always — всегда",
    )
    parser.add_argument("--show-browser", action="store_true", help="показывать окно браузера")
    parser.add_argument("--no-color", action="store_true", help="не подкрашивать колонку «Есть СРО»")

    parser.add_argument("--nostroy-url", default="", help="свой адрес API НОСТРОЙ")
    parser.add_argument("--nopriz-url", default="", help="свой адрес API НОПРИЗ")
    parser.add_argument("--probe", default="", help="режим диагностики: проверить один ИНН и показать подробности")

    args = parser.parse_args(argv)

    if not args.output:
        args.output = default_output(args.input)
    stem = os.path.splitext(args.output)[0]
    if not args.cache:
        args.cache = f"{stem}_кэш.json"
    if not args.log:
        args.log = f"{stem}_лог.txt"
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    log = Log(args.log)
    try:
        if args.probe:
            return run_probe(args, log)
        return run(args, log)
    finally:
        log.close()


if __name__ == "__main__":
    raise SystemExit(main())
