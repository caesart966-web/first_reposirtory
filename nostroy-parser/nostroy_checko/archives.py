"""
Распаковка архивов (.zip и .rar), в том числе вложенных.

Особенности, которые важны для реальных выгрузок реестров:

* русские имена файлов внутри ZIP, созданного в Windows, приходят в кодировке
  cp866/cp1251 и без правильной обработки превращаются в «крякозябры»;
* архив может содержать архивы (частая ситуация: «Реестр.zip» -> «СРО-410.rar»);
* защита от «zip slip» — путей вида ``../../etc/passwd`` внутри архива;
* для .rar нужен внешний распаковщик: библиотека ``rarfile`` использует
  ``unrar``/``unar``/``bsdtar``/``7z``. Если их нет, выдаём понятную инструкцию,
  а не невнятную трассировку.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

from .config import ARCHIVE_EXTENSIONS, IGNORED_DIR_NAMES, IGNORED_NAME_PREFIXES
from .logging_setup import get_logger

logger = get_logger("archives")

#: Максимальная глубина вложенности архивов (защита от «архивной бомбы»).
MAX_ARCHIVE_DEPTH = 5

#: Внешние распаковщики RAR, которые пробуем по очереди, если ``rarfile`` не смог.
_RAR_FALLBACK_TOOLS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("7z", ("x", "-y", "-o{dest}", "{archive}")),
    ("7zz", ("x", "-y", "-o{dest}", "{archive}")),
    ("unar", ("-quiet", "-force-overwrite", "-output-directory", "{dest}", "{archive}")),
    ("bsdtar", ("-x", "-f", "{archive}", "-C", "{dest}")),
    ("unrar", ("x", "-y", "{archive}", "{dest}/")),
)

RAR_HELP_MESSAGE = (
    "Не удалось распаковать RAR-архив: в системе нет внешнего распаковщика.\n"
    "Установите один из вариантов:\n"
    "  • Windows : скачайте WinRAR/UnRAR (unrar.exe) и добавьте его в PATH;\n"
    "  • macOS   : brew install unar   (или brew install rar);\n"
    "  • Ubuntu  : sudo apt-get install unrar   (или sudo apt-get install unar / p7zip-full);\n"
    "  • любая ОС: pip install rarfile и установите 7-Zip (7z) в PATH.\n"
    "Как обходной путь: распакуйте архив вручную и передайте скрипту папку "
    "или отдельный Excel-файл."
)


class ArchiveError(RuntimeError):
    """Ошибка распаковки архива с понятным пользователю сообщением."""


# --------------------------------------------------------------------------- #
#                              Вспомогательное                                 #
# --------------------------------------------------------------------------- #

def is_archive(path: Path) -> bool:
    """Является ли файл поддерживаемым архивом (по расширению)."""
    return path.suffix.lower() in ARCHIVE_EXTENSIONS


def _is_ignored(name: str) -> bool:
    """Служебные файлы ОС и временные файлы Excel пропускаем."""
    base = name.rsplit("/", 1)[-1]
    if any(base.startswith(prefix) for prefix in IGNORED_NAME_PREFIXES):
        return True
    return any(part in IGNORED_DIR_NAMES for part in name.replace("\\", "/").split("/"))


def _decode_zip_name(info: zipfile.ZipInfo) -> str:
    """
    Восстанавливает исходное имя файла из ZIP.

    Если в архиве не выставлен флаг UTF-8 (бит 0x800), Python декодирует имя
    как cp437 — для русских имён это мусор. Возвращаем байты обратно и
    пробуем кириллические кодировки.
    """
    if info.flag_bits & 0x800:
        return info.filename
    try:
        raw = info.filename.encode("cp437")
    except UnicodeEncodeError:
        return info.filename
    for encoding in ("cp866", "cp1251", "utf-8"):
        try:
            decoded = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        # Кириллица в cp866 — самый частый случай для архивов из Windows.
        if any("а" <= ch.lower() <= "я" or ch in "ЁёIiI" for ch in decoded):
            return decoded
    return info.filename


def _safe_target(dest_dir: Path, member_name: str) -> Path | None:
    """
    Строит безопасный путь распаковки внутри ``dest_dir``.

    Возвращает ``None``, если элемент архива пытается «выпрыгнуть» наружу
    (абсолютный путь или ``..``) — такие элементы пропускаем с предупреждением.
    """
    cleaned = member_name.replace("\\", "/").lstrip("/")
    parts = [part for part in cleaned.split("/") if part not in ("", ".", "..")]
    if not parts:
        return None
    # Убираем символы, недопустимые в именах файлов Windows.
    parts = ["".join(ch for ch in part if ch not in '<>:"|?*') or "_" for part in parts]
    target = (dest_dir / Path(*parts)).resolve()
    try:
        target.relative_to(dest_dir.resolve())
    except ValueError:
        return None
    return target


# --------------------------------------------------------------------------- #
#                                    ZIP                                       #
# --------------------------------------------------------------------------- #

def extract_zip(archive_path: Path, dest_dir: Path) -> list[Path]:
    """Распаковывает ZIP-архив, корректно обрабатывая русские имена файлов."""
    extracted: list[Path] = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                name = _decode_zip_name(info)
                if info.is_dir() or _is_ignored(name):
                    continue
                target = _safe_target(dest_dir, name)
                if target is None:
                    logger.warning("Пропущен небезопасный путь в архиве: %r", name)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with archive.open(info) as source, open(target, "wb") as output:
                        shutil.copyfileobj(source, output)
                except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
                    # Одна битая запись не должна ронять разбор всего архива.
                    logger.error("Не удалось извлечь %r из %s: %s", name, archive_path.name, exc)
                    continue
                extracted.append(target)
    except zipfile.BadZipFile as exc:
        raise ArchiveError(f"Файл {archive_path} не является корректным ZIP-архивом: {exc}") from exc
    return extracted


# --------------------------------------------------------------------------- #
#                                    RAR                                       #
# --------------------------------------------------------------------------- #

def _extract_rar_with_library(archive_path: Path, dest_dir: Path) -> list[Path] | None:
    """
    Пытается распаковать RAR через библиотеку ``rarfile``.

    Возвращает список файлов или ``None``, если библиотека недоступна либо
    не нашла внешний распаковщик (тогда сработает запасной вариант).
    """
    try:
        import rarfile  # необязательная зависимость
    except ImportError:
        logger.debug("Библиотека rarfile не установлена")
        return None

    try:
        with rarfile.RarFile(str(archive_path)) as archive:
            extracted: list[Path] = []
            for info in archive.infolist():
                name = info.filename
                if info.is_dir() or _is_ignored(name):
                    continue
                target = _safe_target(dest_dir, name)
                if target is None:
                    logger.warning("Пропущен небезопасный путь в архиве: %r", name)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with archive.open(info) as source, open(target, "wb") as output:
                        shutil.copyfileobj(source, output)
                except Exception as exc:  # noqa: BLE001 — любая ошибка одного файла не критична
                    logger.error("Не удалось извлечь %r из %s: %s", name, archive_path.name, exc)
                    continue
                extracted.append(target)
            return extracted
    except Exception as exc:  # noqa: BLE001 — тип исключения зависит от версии rarfile
        logger.debug("rarfile не справился с %s: %s", archive_path.name, exc)
        return None


def _extract_rar_with_external_tool(archive_path: Path, dest_dir: Path) -> list[Path] | None:
    """Запасной вариант: распаковка внешней утилитой (7z / unar / bsdtar / unrar)."""
    for tool, args_template in _RAR_FALLBACK_TOOLS:
        executable = shutil.which(tool)
        if not executable:
            continue
        args = [
            arg.format(dest=str(dest_dir), archive=str(archive_path))
            for arg in args_template
        ]
        logger.info("Распаковка RAR внешней утилитой %s", tool)
        try:
            completed = subprocess.run(
                [executable, *args],
                capture_output=True,
                timeout=1800,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Утилита %s завершилась ошибкой: %s", tool, exc)
            continue
        if completed.returncode == 0:
            return [path for path in dest_dir.rglob("*") if path.is_file()]
        logger.warning(
            "Утилита %s вернула код %s: %s",
            tool,
            completed.returncode,
            completed.stderr.decode("utf-8", errors="replace")[:400],
        )
    return None


def extract_rar(archive_path: Path, dest_dir: Path) -> list[Path]:
    """Распаковывает RAR-архив всеми доступными способами."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    result = _extract_rar_with_library(archive_path, dest_dir)
    if result:
        return result
    result = _extract_rar_with_external_tool(archive_path, dest_dir)
    if result is not None:
        return result
    raise ArchiveError(f"{RAR_HELP_MESSAGE}\nАрхив: {archive_path}")


# --------------------------------------------------------------------------- #
#                             Публичная точка входа                            #
# --------------------------------------------------------------------------- #

def extract_archive(archive_path: Path, dest_dir: Path, depth: int = 0) -> list[Path]:
    """
    Рекурсивно распаковывает архив в ``dest_dir``.

    Вложенные архивы распаковываются в подпапки с суффиксом ``__unpacked``,
    их содержимое тоже попадает в результат. Порядок папок внутри архива
    сохраняется — по ТЗ структура может быть любой, и мы её не «выпрямляем».

    :return: список путей ко всем извлечённым файлам (без самих архивов).
    """
    if depth > MAX_ARCHIVE_DEPTH:
        logger.warning("Достигнута максимальная глубина вложенности архивов: %s", archive_path)
        return []

    suffix = archive_path.suffix.lower()
    logger.info("Распаковка архива: %s -> %s", archive_path.name, dest_dir)
    if suffix == ".zip":
        files = extract_zip(archive_path, dest_dir)
    elif suffix == ".rar":
        files = extract_rar(archive_path, dest_dir)
    else:
        raise ArchiveError(
            f"Неподдерживаемый формат архива: {archive_path.suffix!r}. "
            f"Поддерживаются: {', '.join(sorted(ARCHIVE_EXTENSIONS))}"
        )

    logger.info("Извлечено файлов: %d", len(files))

    # --- рекурсивно разбираем вложенные архивы ----------------------------- #
    result: list[Path] = []
    for path in files:
        if is_archive(path):
            nested_dir = path.parent / f"{path.stem}__unpacked"
            try:
                result.extend(extract_archive(path, nested_dir, depth + 1))
            except ArchiveError as exc:
                # Вложенный архив может быть битым — это не повод останавливать всё.
                logger.error("Вложенный архив пропущен: %s", exc)
        else:
            result.append(path)
    return result
