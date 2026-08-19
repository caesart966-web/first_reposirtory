"""
Оркестрация всего процесса.

Порядок работы:

1. подготовка структуры папок ``output/``;
2. приём входных данных: архив ``.rar``/``.zip``, отдельный Excel-файл или папка;
3. рекурсивный поиск всех таблиц и чтение ВСЕХ листов;
4. разбор строк в записи членов СРО;
5. группировка (одна компания — один запрос к checko.ru);
6. обогащение контактами с checko.ru в несколько потоков с соблюдением
   суточной квоты и сохранением прогресса;
7. запись итогового Excel-отчёта.

Пункт 6 устроен так, что скрипт можно останавливать и запускать заново
хоть каждый день: всё уже собранное лежит в файле состояния, а счётчик
квоты сам обнуляется в 00:00.
"""

from __future__ import annotations

import shutil
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # только для аннотаций — среда выполнения этот импорт не видит
    from .nostroy_api import NostroyMemberInfo

from .archives import extract_archive, is_archive
from .checko_api import CheckoApiClient
from .checko_client import CheckoClient
from .config import Settings
from .excel_reader import find_data_files, iter_sheets
from .logging_setup import get_logger
from .models import (
    STATUS_FORBIDDEN,
    STATUS_RATE_LIMITED,
    STATUS_SKIPPED,
    CheckoContacts,
    CompanyGroup,
    RegistryRecord,
    UnrecognizedRow,
)
from .registry_parser import group_records, parse_sheet
from .report import write_parsed_artifacts, write_report
from .state import StateStore

logger = get_logger("pipeline")


@dataclass(slots=True)
class RunResult:
    """Итог одного запуска — используется в логах, сводке и тестах."""

    records: list[RegistryRecord] = field(default_factory=list)
    groups: list[CompanyGroup] = field(default_factory=list)
    unrecognized: list[UnrecognizedRow] = field(default_factory=list)
    files_index: list[dict[str, Any]] = field(default_factory=list)
    report_path: Path | None = None
    checko_done: int = 0            # успешно обработано компаний за этот запуск
    checko_failed: int = 0          # ошибок за этот запуск
    checko_pending: int = 0         # осталось на следующие дни
    quota_used: int = 0
    quota_limit: int = 0
    interrupted: bool = False       # работа прервана (лимит/Ctrl+C)
    forbidden_seen: bool = False    # сервис отклонил ключ / доступ (403)
    in_report: int = 0              # сколько компаний уже вошло в отчёт

    def summary(self) -> dict[str, Any]:
        """Сводка для служебной вкладки отчёта и финального сообщения."""
        return {
            "Записей реестра всего": len(self.records),
            "Уникальных компаний": len(self.groups),
            "Компаний в отчёте (обработано)": self.in_report,
            "Нераспознанных строк": len(self.unrecognized),
            "Обработано файлов": len(self.files_index),
            "Запросов к checko.ru за запуск": self.checko_done + self.checko_failed,
            "Успешных запросов checko.ru": self.checko_done,
            "Ошибок checko.ru": self.checko_failed,
            "Осталось компаний на следующие дни": self.checko_pending,
            "Квота использована": f"{self.quota_used}/{self.quota_limit}",
            "Работа прервана лимитом": "да" if self.interrupted else "нет",
        }


# --------------------------------------------------------------------------- #
#                             Шаг 1: входные данные                            #
# --------------------------------------------------------------------------- #

def prepare_input(settings: Settings) -> Path:
    """
    Готовит данные к разбору и возвращает корневую папку для поиска таблиц.

    * архив ``.rar``/``.zip`` — копируется в ``raw_data/`` и распаковывается
      в ``raw_data/extracted/`` (с сохранением любой структуры вложенных папок);
    * отдельный Excel/CSV — копируется в ``raw_data/``;
    * папка — используется как есть (копия не делается, чтобы не дублировать
      гигабайты данных), путь запоминается в отчёте.
    """
    source = settings.input_path
    if not source.exists():
        raise FileNotFoundError(f"Входной путь не найден: {source}")

    settings.ensure_dirs()

    if source.is_dir():
        logger.info("Входные данные — папка: %s", source)
        return source

    if is_archive(source):
        copied = settings.raw_data_dir / source.name
        if copied.resolve() != source.resolve():
            shutil.copy2(source, copied)
            logger.info("Архив скопирован в %s", copied)
        else:
            copied = source
        extracted = extract_archive(copied, settings.extracted_dir)
        logger.info("Из архива извлечено файлов: %d", len(extracted))
        return settings.extracted_dir

    # Одиночный файл таблицы.
    copied = settings.raw_data_dir / source.name
    if copied.resolve() != source.resolve():
        shutil.copy2(source, copied)
        logger.info("Файл скопирован в %s", copied)
    else:
        copied = source
    return copied


# --------------------------------------------------------------------------- #
#                          Шаг 2: разбор всех таблиц                           #
# --------------------------------------------------------------------------- #

def parse_all(settings: Settings, search_root: Path) -> RunResult:
    """Находит все таблицы, читает все листы и собирает записи реестра."""
    result = RunResult()

    files = find_data_files(search_root)
    if not files:
        logger.warning(
            "В %s не найдено ни одного файла с расширениями .xlsx/.xlsm/.xls/.xlsb/.csv",
            search_root,
        )
        return result

    logger.info("Найдено файлов для разбора: %d", len(files))
    root = search_root if search_root.is_dir() else search_root.parent

    # Статистика по каждому файлу — попадает в parsed/files_index.csv.
    per_file: dict[str, dict[str, Any]] = {}

    for sheet in iter_sheets(files, root):
        stats = per_file.setdefault(
            sheet.display_path,
            {"file": sheet.display_path, "sheets": 0, "rows": 0, "records": 0, "unrecognized": 0},
        )
        stats["sheets"] += 1
        stats["rows"] += sheet.row_count

        records, unrecognized, _ = parse_sheet(
            sheet,
            scan_rows=settings.header_scan_rows,
            max_span=settings.header_max_span,
            sample_size=settings.content_sample,
        )
        stats["records"] += len(records)
        stats["unrecognized"] += len(unrecognized)
        result.records.extend(records)
        result.unrecognized.extend(unrecognized)

    result.files_index = list(per_file.values())
    logger.info(
        "Разбор завершён: записей %d, нераспознанных строк %d",
        len(result.records), len(result.unrecognized),
    )
    return result


# --------------------------------------------------------------------------- #
#                 Шаг 2б: даты членства из реестра НОСТРОЙ                     #
# --------------------------------------------------------------------------- #

def _apply_nostroy(group: CompanyGroup, info: "NostroyMemberInfo") -> None:
    """Переносит сведения из реестра НОСТРОЙ в группу компании."""
    group.nostroy_date_join = info.date_join
    group.nostroy_date_exit = info.date_exit
    group.nostroy_status = info.status_text
    group.nostroy_phones = list(info.phones)
    group.nostroy_emails = list(info.emails)
    group.nostroy_addresses = list(info.addresses)
    group.nostroy_directors = list(info.directors)


def enrich_dates_from_nostroy(
    groups: list[CompanyGroup],
    settings: Settings,
    state: StateStore,
) -> None:
    """
    Дотягивает даты вступления/исключения из открытого реестра НОСТРОЙ.

    Запрашиваются только компании, у которых в файле выгрузки нет даты
    вступления и есть ИНН. Реестр бесплатный и без ключей, но это общий
    публичный ресурс: частота запросов ограничена, ответы кэшируются в файле
    состояния — повторные запуски реестр не дёргают.
    """
    from .nostroy_api import NostroyClient, NostroyMemberInfo

    def needs(group: CompanyGroup) -> bool:
        # Реестр бесплатный, ответы кэшируются — запрашиваем всех с ИНН:
        # он даёт не только даты, но и адрес/телефон/руководителя.
        return bool(group.inn)

    pending = [group for group in groups if needs(group)]
    if not pending:
        return

    # Сначала раздаём то, что уже в кэше.
    to_fetch: list[CompanyGroup] = []
    for group in pending:
        cached = state.get_nostroy(group.inn)
        if cached is not None:
            _apply_nostroy(group, NostroyMemberInfo.from_dict(cached))
        else:
            to_fetch.append(group)

    if not to_fetch:
        logger.info("Даты из реестра НОСТРОЙ: все %d компаний взяты из кэша", len(pending))
        return

    logger.info(
        "Запрашиваю открытый реестр НОСТРОЙ по %d компаниям — даты членства, "
        "адреса и контакты (бесплатно, без лимита). Уже известных из кэша: %d. "
        "Этот проход разовый: завтра он не повторится",
        len(to_fetch), len(pending) - len(to_fetch),
    )
    client = NostroyClient(
        settings, sample_path=settings.parsed_dir / "nostroy_api_sample.json"
    )
    found = 0
    done = 0
    start_time = time.monotonic()
    stop_event = threading.Event()

    def fetch(group: CompanyGroup) -> tuple[CompanyGroup, Any]:
        if stop_event.is_set() or client.is_dead:
            return group, None
        return group, client.lookup(group.inn)

    # Первую компанию обрабатываем в одиночку: клиент на ней определяет рабочий
    # формат запроса и запоминает его. Если запустить сразу все потоки, каждый
    # из них перебирал бы варианты заново — лишние запросы к чужому серверу.
    executor = ThreadPoolExecutor(max_workers=max(1, settings.nostroy_workers))
    try:
        head, tail = to_fetch[:1], to_fetch[1:]
        for batch in (head, tail):
            if not batch or stop_event.is_set():
                continue
            for group, info in executor.map(fetch, batch):
                done += 1
                if info is None:
                    continue
                state.set_nostroy(group.inn, info.to_dict())
                if info.found:
                    found += 1
                    _apply_nostroy(group, info)
                if done % 50 == 0 or done == len(to_fetch):
                    speed = done / max(time.monotonic() - start_time, 0.001)
                    left = (len(to_fetch) - done) / speed if speed else 0
                    logger.info(
                        "  реестр НОСТРОЙ: %d из %d (найдено: %d, осталось ~%d мин)",
                        done, len(to_fetch), found, int(left / 60) + 1,
                    )
                    state.save(force=False)
                if client.is_dead:
                    stop_event.set()
    except KeyboardInterrupt:
        logger.warning("Запросы к реестру НОСТРОЙ прерваны — собранное сохранено")
        stop_event.set()
    finally:
        stop_event.set()
        executor.shutdown(wait=True, cancel_futures=True)
        client.close()
        state.save(force=True)
    logger.info("Реестр НОСТРОЙ: даты получены по %d из %d компаний", found, len(to_fetch))


# --------------------------------------------------------------------------- #
#                       Шаг 3: обогащение через checko.ru                      #
# --------------------------------------------------------------------------- #

#: Сколько раз автоматически повторять компанию, по которой была ошибка.
#: Больше — бессмысленная трата дефицитной суточной квоты.
MAX_AUTO_RETRY_ATTEMPTS = 3


def _needs_lookup(group: CompanyGroup, state: StateStore, settings: Settings) -> bool:
    """
    Нужно ли запрашивать компанию на checko.ru.

    Правила:

    * по чему есть окончательный ответ (``ok`` или ``not_found``) — не
      запрашиваем никогда: квота слишком дорогая;
    * ``rate_limited``/``skipped`` — это не отказ, а «не успели»: повторяем
      всегда (как раз ради этого и существует запуск на следующий день);
    * ошибки и блокировки повторяем автоматически, но не более
      :data:`MAX_AUTO_RETRY_ATTEMPTS` раз; ключ ``--retry-failed`` снимает
      это ограничение.
    """
    if not group.query_for_checko():
        return False
    if not group.inn and not settings.query_by_name:
        return False
    existing = state.get_result(group.key)
    if existing is None:
        return True

    # Источник данных сменился (например, появился ключ API вместо разбора
    # страниц сайта) — прошлые неудачи больше ничего не значат. Иначе компании,
    # которые не смог найти парсер HTML, навсегда остались бы со статусом
    # not_found и API их бы уже не проверил.
    current_source = "api" if settings.checko_api_key else "html"
    if existing.source and existing.source != current_source and not existing.is_success:
        return True

    if existing.is_final:
        return False
    if existing.status in (STATUS_RATE_LIMITED, STATUS_SKIPPED):
        return True
    if settings.retry_failed:
        return True
    return state.get_attempts(group.key).count < MAX_AUTO_RETRY_ATTEMPTS


def enrich_with_checko(
    groups: list[CompanyGroup],
    settings: Settings,
    state: StateStore,
    result: RunResult,
) -> None:
    """
    Запрашивает контакты на checko.ru в несколько потоков.

    Квота проверяется и списывается атомарно внутри каждого рабочего потока,
    поэтому суточный лимит не превышается независимо от числа потоков.
    Как только лимит исчерпан, оставшиеся компании помечаются как «ожидают»
    и будут обработаны при следующем запуске (на следующий день).
    """
    # --- подставляем уже собранные ранее данные ----------------------------- #
    for group in groups:
        existing = state.get_result(group.key)
        if existing is not None:
            group.checko = existing

    pending = [group for group in groups if _needs_lookup(group, state, settings)]
    if settings.max_companies is not None:
        pending = pending[: settings.max_companies]

    quota = state.quota
    result.quota_limit = quota.limit

    if not pending:
        logger.info("Все компании уже обработаны через checko.ru — новых запросов не требуется")
        result.quota_used = quota.used
        return

    available = quota.remaining
    logger.info(
        "К обработке через checko.ru: %d компаний. %s",
        len(pending), quota.progress_line(),
    )
    if available <= 0:
        logger.warning(
            "Суточная квота уже исчерпана. Запустите скрипт завтра — "
            "он продолжит с того же места (осталось компаний: %d)",
            len(pending),
        )
        result.checko_pending = len(pending)
        result.interrupted = True
        result.quota_used = quota.used
        return

    # Есть ключ API — идём через api.checko.ru: он отдаёт структурированный JSON
    # и не закрыт защитой от автоматизации, в отличие от обычных страниц сайта.
    if settings.checko_api_key:
        logger.info("Источник данных: официальный API checko.ru (api.checko.ru)")
        client = CheckoApiClient(
            settings, quota, sample_path=settings.parsed_dir / "checko_api_sample.json"
        )
    else:
        logger.warning("=" * 70)
        logger.warning("ВНИМАНИЕ: ключ API checko.ru НЕ ЗАДАН.")
        logger.warning("Скрипт попробует разбирать обычные страницы сайта, но сайт")
        logger.warning("защищён от автоматизации и почти наверняка ответит отказом.")
        logger.warning("Впишите ключ в файл checko_api_key.txt рядом со скриптом")
        logger.warning("(ключ выдаётся в личном кабинете checko.ru).")
        logger.warning("=" * 70)
        client = CheckoClient(settings, quota)
    progress_bar = _make_progress_bar(min(len(pending), available), settings)
    processed = 0
    start_time = time.monotonic()
    # Сигнал «немедленно прекратить»: выставляется при Ctrl+C и при блокировке.
    # Без него ThreadPoolExecutor при выходе доработал бы всю очередь до конца.
    stop_event = threading.Event()

    def worker(group: CompanyGroup) -> tuple[CompanyGroup, CheckoContacts | None]:
        """Один запрос к checko.ru; квота бронируется до обращения к сети."""
        if stop_event.is_set() or quota.exhausted or not quota.reserve():
            return group, None
        try:
            contacts = client.lookup(group.query_for_checko(), expected_inn=group.inn)
        except Exception as exc:  # noqa: BLE001 — поток не имеет права падать
            logger.exception("Непредвиденная ошибка по компании %s", group.name)
            contacts = CheckoContacts(
                query=group.query_for_checko(),
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )
        contacts.quota_used = 1
        return group, contacts

    futures: list[Future] = []
    executor = ThreadPoolExecutor(max_workers=max(1, settings.workers))
    try:
        futures = [executor.submit(worker, group) for group in pending]
        for future in futures:
            try:
                group, contacts = future.result()
            except Exception as exc:  # noqa: BLE001
                logger.error("Ошибка рабочего потока: %s", exc)
                result.checko_failed += 1
                continue

            if contacts is None:
                # Квоты не хватило (или работа остановлена) — компания ждёт
                # следующего запуска; в состоянии её результат не портим.
                continue

            group.checko = contacts
            state.set_result(group.key, contacts)
            processed += 1

            if contacts.is_success:
                result.checko_done += 1
            else:
                result.checko_failed += 1

            if progress_bar is not None:
                progress_bar.update(1)
            elif processed % 5 == 0 or processed == 1:
                logger.info(
                    "Обработано компаний: %d из %d | %s",
                    processed, len(pending), quota.progress_line(),
                )

            state.save(force=False)

            # Лимит или блокировка — дальше идти бессмысленно.
            if contacts.status == STATUS_FORBIDDEN:
                result.forbidden_seen = True
            if quota.exhausted or contacts.status == STATUS_FORBIDDEN:
                if not result.interrupted:
                    if contacts.status == STATUS_FORBIDDEN:
                        reason = "checko.ru отказал в доступе (HTTP 403)"
                    else:
                        reason = quota.exhausted_reason or "израсходована суточная квота"
                    logger.warning("Дальнейшие запросы остановлены: %s", reason)
                result.interrupted = True
                stop_event.set()
    except KeyboardInterrupt:
        logger.warning("Прервано пользователем — сохраняю собранные данные")
        result.interrupted = True
        stop_event.set()
    finally:
        # cancel_futures=True снимает ещё не начатые задачи: без этого выход
        # из executor'а «доработал» бы всю очередь, игнорируя остановку.
        stop_event.set()
        executor.shutdown(wait=True, cancel_futures=True)
        if progress_bar is not None:
            progress_bar.close()
        if hasattr(client, "report_skipped"):
            client.report_skipped()
        client.close()
        state.save(force=True)

    # Компании, до которых не дошла очередь (квота кончилась по пути).
    result.checko_pending = sum(
        1 for group in pending if group.checko is None or not group.checko.is_final
    )
    result.quota_used = quota.used

    elapsed = time.monotonic() - start_time
    logger.info(
        "checko.ru: успешно %d, ошибок %d, осталось на потом %d, время %.1f с",
        result.checko_done, result.checko_failed, result.checko_pending, elapsed,
    )
    if quota.exhausted and result.checko_pending:
        logger.warning(
            "Суточный лимит checko.ru исчерпан. Осталось компаний: %d. "
            "Запустите ту же команду завтра — скрипт продолжит с этого места.",
            result.checko_pending,
        )


def _make_progress_bar(total: int, settings: Settings) -> Any:
    """Создаёт прогресс-бар tqdm, если библиотека доступна и вывод не отключён."""
    if settings.no_progress_bar or total <= 0:
        return None
    try:
        from tqdm import tqdm
    except ImportError:
        return None
    return tqdm(total=total, desc="checko.ru", unit="комп.", ncols=100)


# --------------------------------------------------------------------------- #
#                                Полный прогон                                 #
# --------------------------------------------------------------------------- #

def run(settings: Settings) -> RunResult:
    """
    Выполняет полный цикл обработки и возвращает результат.

    Функция не выбрасывает исключений на «ожидаемых» проблемах (пустой ввод,
    ошибки отдельных файлов, недоступность checko.ru) — вместо этого пишет
    их в лог и делает максимум возможного с имеющимися данными.
    """
    settings.ensure_dirs()

    # --- вход ---------------------------------------------------------------- #
    search_root = prepare_input(settings)

    # --- разбор -------------------------------------------------------------- #
    result = parse_all(settings, search_root)
    if not result.records:
        logger.warning("Записей членов СРО не найдено — отчёт будет пустым")

    # --- группировка --------------------------------------------------------- #
    result.groups = group_records(result.records, settings.dedupe_by)

    # --- состояние ----------------------------------------------------------- #
    state = StateStore(settings.state_file, daily_limit=settings.daily_limit)
    state.load()
    if settings.reset_state:
        state.reset()
    state.set_meta(
        input_path=str(settings.input_path),
        total_companies=len(result.groups),
        total_records=len(result.records),
    )

    # --- даты членства из открытого реестра НОСТРОЙ -------------------------- #
    if settings.nostroy_dates:
        enrich_dates_from_nostroy(result.groups, settings, state)

    # --- checko.ru ----------------------------------------------------------- #
    if settings.use_checko:
        enrich_with_checko(result.groups, settings, state, result)
    else:
        logger.info("Запросы к checko.ru отключены (--no-checko) — только разбор реестра")
        for group in result.groups:
            existing = state.get_result(group.key)
            if existing is not None:
                group.checko = existing
        result.quota_limit = state.quota.limit
        result.quota_used = state.quota.used

    state.save(force=True)

    # --- выгрузки ------------------------------------------------------------ #
    write_parsed_artifacts(
        settings.parsed_dir,
        result.records,
        result.groups,
        result.unrecognized,
        result.files_index,
    )

    result.in_report = sum(
        1 for group in result.groups
        if group.checko is not None and group.checko.is_final
    )
    result.report_path = write_report(settings.report_path, result.groups)
    return result
