"""сро_checko.py: все разделы в один JSON, страницы дел, остановка на лимите."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("сро_checko", ROOT / "сро_checko.py")
сро = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(сро)


class Ответ:
    def __init__(self, code, payload):
        self.status_code, self._payload = code, payload

    def json(self):
        if self._payload is None:
            raise ValueError
        return self._payload


class Сеть:
    def __init__(self, ответ):
        self.ответ, self.журнал = ответ, []

    def get(self, url, params=None, timeout=None):
        раздел = url.rsplit("/", 1)[1]
        self.журнал.append((раздел, params.get("page")))
        return self.ответ(раздел, params)


class TestСбор(unittest.TestCase):
    def запустить(self, ответ):
        сеть = Сеть(ответ)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(сро.requests, "Session", return_value=сеть), \
                mock.patch.object(сро.time, "sleep"):
            out = Path(tmp) / "x.json"
            код = сро.main(["--inn", "7713387201", "--key", "к", "--out", str(out)])
            return код, json.loads(out.read_text(encoding="utf-8")), сеть.журнал

    def test_все_разделы_и_страницы_дел(self):
        def ответ(раздел, params):
            if раздел == "legal-cases":
                return Ответ(200, {"data": {"СтрВсего": 3, "Записи": [params.get("page") or 1]}})
            return Ответ(200, {"data": {"раздел": раздел}, "meta": {"status": "ok"}})
        код, итог, журнал = self.запустить(ответ)
        self.assertEqual(код, 0)
        self.assertEqual(set(итог["ответы"]), set(сро.РАЗДЕЛЫ))
        self.assertEqual([p["data"]["Записи"] for p in итог["ответы"]["legal-cases"]], [[1], [2], [3]])
        self.assertEqual(len(журнал), 7)                 # 5 разделов + 2 страницы дел
        self.assertEqual(итог["ошибки"], {})

    def test_лимит_останавливает_и_сохраняет_собранное(self):
        def ответ(раздел, params):
            if раздел == "legal-cases":
                return Ответ(403, {"meta": {"status": "error", "message": "Исчерпан лимит"}})
            return Ответ(200, {"data": {"раздел": раздел}})
        код, итог, журнал = self.запустить(ответ)
        self.assertEqual(код, 2)
        self.assertEqual(set(итог["ответы"]), {"company", "finances"})
        self.assertEqual(итог["ошибки"], {"legal-cases": "HTTP 403"})
        self.assertEqual(len(журнал), 3)

    def test_ошибка_раздела_не_роняет_остальные(self):
        def ответ(раздел, params):
            if раздел == "inspections":
                return Ответ(200, {"meta": {"status": "error", "message": "Нет данных"}})
            return Ответ(200, {"data": {}})
        код, итог, _ = self.запустить(ответ)
        self.assertEqual(код, 0)
        self.assertEqual(итог["ошибки"], {"inspections": "Нет данных"})
        self.assertIn("enforcements", итог["ответы"])

    def test_ключ_не_пишется_в_файл(self):
        код, итог, _ = self.запустить(lambda раздел, params: Ответ(200, {"data": {}}))
        self.assertNotIn('"к"', json.dumps(итог, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
