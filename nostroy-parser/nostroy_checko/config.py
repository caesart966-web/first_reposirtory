"""
Настройки запуска и глобальные константы.

Никаких «зашитых» путей: все пути приходят из аргументов командной строки
(см. :mod:`main`) и складываются в :class:`Settings`. Значения по умолчанию
рассчитываются относительно текущей рабочей директории пользователя.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# --------------------------------------------------------------------------- #
#                              Форматы файлов                                  #
# --------------------------------------------------------------------------- #

#: Расширения Excel-файлов, которые скрипт умеет читать.
EXCEL_EXTENSIONS: frozenset[str] = frozenset({".xlsx", ".xlsm", ".xls", ".xltx", ".xltm", ".xlsb"})

#: Текстовые табличные форматы (часто встречаются в выгрузках из 1С).
CSV_EXTENSIONS: frozenset[str] = frozenset({".csv", ".tsv", ".txt"})

#: Поддерживаемые архивы.
ARCHIVE_EXTENSIONS: frozenset[str] = frozenset({".zip", ".rar"})

#: Служебные файлы/папки, которые надо игнорировать при обходе (мусор ОС и Excel).
IGNORED_NAME_PREFIXES: tuple[str, ...] = ("~$", "._")
IGNORED_DIR_NAMES: frozenset[str] = frozenset({"__MACOSX", ".git", ".svn", "__pycache__"})

# --------------------------------------------------------------------------- #
#                                  checko.ru                                   #
# --------------------------------------------------------------------------- #

CHECKO_BASE_URL = "https://checko.ru"
CHECKO_SEARCH_PATH = "/search"

#: Бесплатный лимит запросов в сутки (сброс в 00:00 по локальному времени).
DEFAULT_DAILY_LIMIT = 100

#: User-Agent по умолчанию — обычный десктопный браузер.
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

#: Имя файла, в котором можно хранить ключ API рядом со скриптом —
#: так его не приходится каждый раз набирать в командной строке.
CHECKO_KEY_FILENAME = "checko_api_key.txt"

#: Текст-заглушка в этом файле: пока он там, считаем, что ключ не задан.
CHECKO_KEY_PLACEHOLDER = "ВСТАВЬТЕ_КЛЮЧ_СЮДА"


def read_api_key_file(directory: Path) -> str | None:
    """
    Читает ключ API из файла ``checko_api_key.txt`` рядом со скриптом.

    Строки-комментарии (начинаются с ``#``) и заглушка игнорируются.
    Возвращает ``None``, если файла нет или ключ в него ещё не вписан.
    """
    path = directory / CHECKO_KEY_FILENAME
    try:
        content = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    for line in content.splitlines():
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if CHECKO_KEY_PLACEHOLDER in candidate:
            continue
        return candidate
    return None


#: Собственные контакты checko.ru — их нельзя принимать за контакты компании.
CHECKO_OWN_EMAILS: frozenset[str] = frozenset(
    {
        "info@checko.ru",
        "support@checko.ru",
        "help@checko.ru",
        "mail@checko.ru",
        "sales@checko.ru",
        "partner@checko.ru",
        "press@checko.ru",
    }
)
CHECKO_OWN_EMAIL_DOMAINS: frozenset[str] = frozenset({"checko.ru", "checko.com"})

#: Телефоны самого сервиса (в нормализованном виде +7XXXXXXXXXX).
CHECKO_OWN_PHONES: frozenset[str] = frozenset({"+78002225614", "+74952152614"})

# --------------------------------------------------------------------------- #
#                         Значения по умолчанию для CLI                        #
# --------------------------------------------------------------------------- #

DEFAULT_WORKERS = 4               # число параллельных потоков к checko.ru
DEFAULT_RPS = 1.0                 # максимум запросов в секунду суммарно
DEFAULT_TIMEOUT = 25.0            # таймаут одного HTTP-запроса, секунды
DEFAULT_MAX_RETRIES = 3           # повторы при сетевых ошибках и 5xx
DEFAULT_HEADER_SCAN_ROWS = 60     # сколько верхних строк листа смотреть в поисках шапки
DEFAULT_HEADER_MAX_SPAN = 3       # максимум строк в «многоэтажной» шапке
DEFAULT_CONTENT_SAMPLE = 400      # сколько значений колонки анализировать при автодетекте


@dataclass(slots=True)
class Settings:
    """Полный набор параметров одного запуска скрипта."""

    # --- пути -------------------------------------------------------------- #
    input_path: Path                       # входной архив / Excel-файл / папка
    output_dir: Path                       # корень результатов (output/)

    # --- поведение парсера ------------------------------------------------- #
    dedupe_by: str = "inn"                 # "inn" | "name_inn"
    header_scan_rows: int = DEFAULT_HEADER_SCAN_ROWS
    header_max_span: int = DEFAULT_HEADER_MAX_SPAN
    content_sample: int = DEFAULT_CONTENT_SAMPLE

    # --- checko.ru --------------------------------------------------------- #
    use_checko: bool = True                # False => только разбор реестра
    checko_api_key: str | None = None      # ключ официального API (надёжнее HTML)
    daily_limit: int = DEFAULT_DAILY_LIMIT
    workers: int = DEFAULT_WORKERS
    rps: float = DEFAULT_RPS
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    user_agent: str = DEFAULT_USER_AGENT
    proxy: str | None = None
    query_by_name: bool = True             # искать по названию, если нет ИНН
    count_http_requests: bool = False      # квота на каждый HTTP-запрос, а не на компанию
    retry_failed: bool = False             # повторить ранее неудачные запросы
    reset_state: bool = False              # начать «с нуля», удалив прогресс
    max_companies: int | None = None       # ограничение числа компаний (для отладки)

    # --- прочее ------------------------------------------------------------ #
    log_level: str = "INFO"
    with_diagnostics: bool = False         # добавить в отчёт служебные вкладки
    report_date: date = field(default_factory=date.today)
    no_progress_bar: bool = False

    # ---------------------- производные пути (свойства) -------------------- #

    @property
    def raw_data_dir(self) -> Path:
        """`output/raw_data/` — копии исходных файлов и распакованный архив."""
        return self.output_dir / "raw_data"

    @property
    def extracted_dir(self) -> Path:
        """`output/raw_data/extracted/` — содержимое архива."""
        return self.raw_data_dir / "extracted"

    @property
    def parsed_dir(self) -> Path:
        """`output/parsed/` — промежуточные результаты разбора."""
        return self.output_dir / "parsed"

    @property
    def state_dir(self) -> Path:
        """`output/state/` — файл прогресса для продолжения на следующий день."""
        return self.output_dir / "state"

    @property
    def logs_dir(self) -> Path:
        """`output/logs/` — логи запусков."""
        return self.output_dir / "logs"

    @property
    def state_file(self) -> Path:
        """Путь к JSON-файлу состояния (квота + уже собранные данные)."""
        return self.state_dir / "checko_state.json"

    @property
    def report_path(self) -> Path:
        """Итоговый файл `output/final_report_YYYY-MM-DD.xlsx`."""
        return self.output_dir / f"final_report_{self.report_date.isoformat()}.xlsx"

    # ------------------------------ методы --------------------------------- #

    def ensure_dirs(self) -> None:
        """Создаёт всю структуру выходных папок (идемпотентно)."""
        for path in (
            self.output_dir,
            self.raw_data_dir,
            self.extracted_dir,
            self.parsed_dir,
            self.state_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def proxies(self) -> dict[str, str] | None:
        """Словарь прокси для requests (или None, если прокси не задан)."""
        if self.proxy:
            return {"http": self.proxy, "https": self.proxy}
        # Уважаем системные переменные окружения, если они заданы.
        env_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if env_proxy:
            return {"http": env_proxy, "https": env_proxy}
        return None
