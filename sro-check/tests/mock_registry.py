"""Локальный «поддельный реестр» для тестов.

Настоящие reestr.nostroy.ru и nopriz.ru в тестах не дёргаются: во-первых, это
государственные сервисы, во-вторых, тест должен быть воспроизводимым.
Мок умеет отвечать так же, как реальный API, и так же, как он ломается.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Наборы ответов: ИНН -> сценарий
# ---------------------------------------------------------------------------

def valid_inn(prefix9: str) -> str:
    """Достроить 9 цифр до корректного ИНН, посчитав контрольный разряд.

    ИНН в тестах — выдуманные, но с правильной контрольной суммой: программа
    сознательно не ходит в реестр за ИНН, не прошедшим проверку.
    """
    weights = (2, 4, 10, 3, 5, 9, 4, 6, 8)
    control = sum(int(d) * w for d, w in zip(prefix9, weights)) % 11 % 10
    return prefix9 + str(control)


MEMBER_INN = valid_inn("770000001")  # есть в реестре, членство действует
SUSPENDED_INN = valid_inn("770000002")  # есть в реестре, членство приостановлено
EXCLUDED_INN = valid_inn("770000003")  # исключён
NON_MEMBER_INN = valid_inn("770000004")  # достоверно нет в реестре
SERVER_ERROR_INN = valid_inn("770000005")  # сервер отвечает 500
HTML_INN = valid_inn("770000006")  # вместо JSON приходит HTML-заглушка
WEIRD_JSON_INN = valid_inn("770000007")  # JSON незнакомой структуры
NO_INN_FIELD_INN = valid_inn("770000008")  # записи есть, но без поля ИНН
UNFILTERED_INN = valid_inn("770000009")  # поиск проигнорирован, отдан весь реестр
PAGINATED_INN = valid_inn("770000010")  # выдана лишь часть результатов
TIMEOUT_INN = valid_inn("770000011")  # соединение обрывается


def _member_record(inn: str, company: str, status: str, number: str) -> dict:
    return {
        "id": 4242,
        "inn": inn,
        "ogrn": "1027700132195",
        "full_description": company,
        "registry_number": number,
        "member_status": status,
        "sro": {
            "id": 55,
            "inn": "7710478632",
            "full_description": "Ассоциация «Саморегулируемая организация «Строители России»",
            "registration_number": "СРО-С-123-45678910",
        },
    }


def _envelope(records: list[dict], count: int | None = None) -> dict:
    return {
        "success": True,
        "data": {"data": records, "count": len(records) if count is None else count},
    }


SCENARIOS: dict[str, dict] = {
    MEMBER_INN: _envelope(
        [_member_record(MEMBER_INN, "ООО «Мостострой»", "Является членом СРО", "1234")]
    ),
    SUSPENDED_INN: _envelope(
        [
            _member_record(
                SUSPENDED_INN,
                "АО «Проектстрой»",
                "Действие членства приостановлено",
                "5678",
            )
        ]
    ),
    EXCLUDED_INN: _envelope(
        [_member_record(EXCLUDED_INN, "ООО «Бывший член»", "Исключен из реестра", "9012")]
    ),
    NON_MEMBER_INN: _envelope([]),
    WEIRD_JSON_INN: {"status": "ok", "payload": {"unexpected": True, "value": 42}},
    NO_INN_FIELD_INN: {
        "success": True,
        "data": {
            "data": [{"id": 7, "full_description": "ООО «Без ИНН»", "member_status": "Действует"}],
            "count": 1,
        },
    },
    UNFILTERED_INN: _envelope(
        [
            _member_record(f"770000000{i}", f"ООО «Чужая компания {i}»", "Является членом СРО", str(i))
            for i in range(1, 9)
        ]
    ),
    PAGINATED_INN: _envelope(
        [
            _member_record("7700000011", "ООО «Другая компания»", "Является членом СРО", "11"),
            _member_record("7700000012", "ООО «Ещё одна»", "Является членом СРО", "12"),
        ],
        count=340,
    ),
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - имя задано базовым классом
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        inn = (query.get("inn") or query.get("searchString") or [""])[0]
        self._respond(inn)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(body)
        except ValueError:
            data = {}
        inn = str(data.get("inn") or data.get("searchString") or "")
        self._respond(inn)

    # ------------------------------------------------------------------

    def _respond(self, inn: str) -> None:
        # Записываем каждый запрос — тесты проверяют, что программа не дёргает
        # реестр лишний раз (кэш, режим перепроверки).
        getattr(self.server, "requests_log", []).append(inn)

        if inn == SERVER_ERROR_INN:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"internal"}')
            return

        if inn == TIMEOUT_INN:
            # Рвём соединение, не отвечая — имитация обрыва связи.
            self.close_connection = True
            try:
                self.connection.close()
            except OSError:
                pass
            return

        if inn == HTML_INN:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body><h1>Сайт на техническом обслуживании</h1></body></html>".encode("utf-8")
            )
            return

        payload = SCENARIOS.get(inn, _envelope([]))
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # тишина в выводе тестов
        pass


class MockRegistry:
    """Запускаемый в фоне мок реестра. Использовать как контекстный менеджер."""

    def __init__(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.requests_log = []  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def requests_log(self) -> list[str]:
        return self.server.requests_log  # type: ignore[attr-defined]

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}/api/sro/all/member/search"

    def __enter__(self) -> "MockRegistry":
        self.thread.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
