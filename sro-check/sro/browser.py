"""Запасной способ проверки — через настоящий браузер (Playwright).

Используется, когда прямые запросы к API не проходят (сменился адрес,
включилась защита от ботов и т.п.).

Хитрость: мы не разбираем вёрстку страницы (она часто меняется), а открываем
страницу поиска, вводим ИНН и ПЕРЕХВАТЫВАЕМ тот самый запрос, который сайт
делает к своему API. Это устойчивее и заодно показывает актуальный адрес API —
его потом можно передать в --nostroy-url / --nopriz-url и работать быстро,
без браузера.
"""

from __future__ import annotations

import re
from typing import Callable

from .models import SOURCE_NOPRIZ, SOURCE_NOSTROY, Outcome, RegistryAnswer
from .registries import interpret_payload

SEARCH_PAGES = {
    SOURCE_NOSTROY: [
        "https://reestr.nostroy.ru/reestr/chleny-sro",
        "https://reestr.nostroy.ru/reestr",
    ],
    SOURCE_NOPRIZ: [
        "https://reestr.nopriz.ru/reestr/chleny-sro",
        "https://reestr.nopriz.ru/reestr",
        "https://nopriz.ru/nreesters/",
    ],
}

# Как выглядит поле поиска — пробуем варианты по очереди
INPUT_SELECTORS = (
    "input[placeholder*='ИНН']",
    "input[placeholder*='инн']",
    "input[placeholder*='Поиск']",
    "input[placeholder*='поиск']",
    "input[type='search']",
    "input[name*='search']",
    "input[name*='inn']",
    "input.search-input",
    "form input[type='text']",
)

_NOT_FOUND_MARKERS = (
    "ничего не найдено",
    "не найдено",
    "нет данных",
    "по вашему запросу",
    "результатов не найдено",
    "no results",
)

_API_HINT = re.compile(r"/api/.*(search|member|reestr)", re.IGNORECASE)


class BrowserLookup:
    """Обёртка над Playwright. Использовать как контекстный менеджер."""

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 45000,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.logger = logger or (lambda message: None)
        self._playwright = None
        self._browser = None
        self._context = None
        self.discovered_urls: dict[str, str] = {}

    def __enter__(self) -> "BrowserLookup":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:  # pragma: no cover - зависит от окружения
            raise RuntimeError(
                "не установлен Playwright. Выполните:\n"
                "    pip install playwright\n"
                "    playwright install chromium"
            ) from error

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            locale="ru-RU",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self._context.set_default_timeout(self.timeout_ms)
        return self

    def __exit__(self, *exc_info) -> None:
        for resource, method in (
            (self._context, "close"),
            (self._browser, "close"),
            (self._playwright, "stop"),
        ):
            if resource is None:
                continue
            try:
                getattr(resource, method)()
            except Exception:  # pragma: no cover - на выходе ошибки уже не важны
                pass

    # ------------------------------------------------------------------

    def lookup(self, source: str, inn: str) -> RegistryAnswer:
        """Проверить ИНН через браузер."""
        if self._context is None:
            return RegistryAnswer(source, Outcome.UNKNOWN, note="браузер не запущен")

        notes: list[str] = []
        for page_url in SEARCH_PAGES.get(source, []):
            try:
                answer = self._lookup_on_page(source, inn, page_url)
            except Exception as error:
                notes.append(f"{page_url}: {type(error).__name__}")
                continue
            if answer.outcome is not Outcome.UNKNOWN:
                return answer
            notes.append(f"{page_url}: {answer.note}")

        return RegistryAnswer(
            source, Outcome.UNKNOWN, note="браузер не смог получить результат — " + "; ".join(notes[:2])
        )

    def _lookup_on_page(self, source: str, inn: str, page_url: str) -> RegistryAnswer:
        page = self._context.new_page()
        captured: list[tuple[str, object]] = []

        def on_response(response) -> None:
            try:
                if not _API_HINT.search(response.url):
                    return
                if response.status != 200:
                    return
                if "json" not in (response.headers.get("content-type") or "").lower():
                    return
                captured.append((response.url, response.json()))
            except Exception:
                pass

        page.on("response", on_response)

        try:
            page.goto(page_url, wait_until="domcontentloaded")

            field = None
            for selector in INPUT_SELECTORS:
                candidate = page.locator(selector).first
                try:
                    if candidate.count() and candidate.is_visible():
                        field = candidate
                        break
                except Exception:
                    continue

            if field is None:
                return RegistryAnswer(source, Outcome.UNKNOWN, note="не нашёл поле поиска на странице")

            field.click()
            field.fill(inn)
            field.press("Enter")

            try:
                page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
            except Exception:
                page.wait_for_timeout(4000)

            # 1) Основной путь: разобрать перехваченный ответ API.
            for url, payload in reversed(captured):
                answer = interpret_payload(payload, inn, source)
                if answer.outcome is not Outcome.UNKNOWN:
                    if source not in self.discovered_urls:
                        self.discovered_urls[source] = url
                        self.logger(f"[{source}] браузер обнаружил адрес API: {url}")
                    return answer

            # 2) Запасной путь: посмотреть на саму страницу. Здесь мы очень
            #    осторожны — «нет» ставим только при явной надписи «не найдено».
            body = (page.inner_text("body") or "").lower()
            if inn in body.replace(" ", ""):
                return RegistryAnswer(
                    source,
                    Outcome.FOUND,
                    memberships=[],
                    note="найдено на странице, но детали не разобраны — проверьте вручную",
                )
            if any(marker in body for marker in _NOT_FOUND_MARKERS):
                return RegistryAnswer(source, Outcome.EMPTY, note="страница сообщила «ничего не найдено»")

            return RegistryAnswer(source, Outcome.UNKNOWN, note="страница не дала понятного результата")
        finally:
            page.close()
