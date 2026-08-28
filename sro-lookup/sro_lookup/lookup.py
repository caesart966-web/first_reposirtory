"""Опрос обоих реестров по списку компаний."""

from __future__ import annotations

from pathlib import Path

from .config import Settings
from .logging_setup import get_logger
from .registry import NOPRIZ_BASE, NOSTROY_BASE, NostroyClient
from .textutils import shorten_company_name, tidy_address

logger = get_logger("sro-lookup")

#: Компания может состоять и в строительной, и в проектной СРО одновременно,
#: поэтому спрашиваем оба реестра, а не останавливаемся на первом ответе.
REGISTRIES = [("НОСТРОЙ", NOSTROY_BASE), ("НОПРИЗ", NOPRIZ_BASE)]


def _unreachable(error: str) -> bool:
    """Реестр не ответил — это не отрицательный ответ, а отсутствие ответа."""
    return "недоступен" in error or "сетевая" in error or "http_код" in error


def lookup_companies(companies: list[tuple[str, str]], settings: Settings) -> list[dict]:
    sample_dir = Path(settings.sample_dir)
    sample_dir.mkdir(parents=True, exist_ok=True)

    clients = [
        (
            title,
            NostroyClient(
                settings,
                sample_path=sample_dir / f"{title.lower()}_sample.json",
                base_url=base,
                title=title,
            ),
        )
        for title, base in REGISTRIES
    ]

    rows: list[dict] = []
    try:
        for position, (name, inn) in enumerate(companies, start=1):
            memberships, unreachable = [], []
            for title, client in clients:
                info = client.lookup(inn, name=name)
                if info.found:
                    memberships.append((title, info))
                elif _unreachable(info.error):
                    unreachable.append(title)

            short_name = shorten_company_name(name) or name
            if memberships:
                for title, info in memberships:
                    rows.append(
                        {
                            "name": short_name,
                            "inn": inn,
                            "sro": info.sro_name,
                            "number": info.sro_number,
                            "registry": title,
                            "status": info.status_text,
                            "join": info.date_join,
                            # Реестр отдаёт адрес вместе с записью о членстве —
                            # он свежее адреса из исходного списка.
                            "address": tidy_address(info.addresses[0]) if info.addresses else "",
                            "note": "" if info.sro_name else "СРО в ответе реестра не указана",
                            "unchecked": False,
                        }
                    )
            else:
                rows.append(
                    {
                        "name": short_name,
                        "inn": inn,
                        "sro": "",
                        "number": "",
                        "registry": "",
                        "status": "",
                        "join": None,
                        "address": "",
                        "note": (
                            "ПРОВЕРКА НЕ ВЫПОЛНЕНА — нет связи с реестром: "
                            + ", ".join(unreachable)
                            if unreachable
                            else "не состоит в СРО (нет записи ни в НОСТРОЙ, ни в НОПРИЗ)"
                        ),
                        "unchecked": bool(unreachable),
                    }
                )
            logger.info("%d/%d  %s — записей о членстве: %d", position, len(companies), inn, len(memberships))
    finally:
        for _, client in clients:
            close = getattr(client, "close", None)
            if callable(close):
                close()
    return rows
