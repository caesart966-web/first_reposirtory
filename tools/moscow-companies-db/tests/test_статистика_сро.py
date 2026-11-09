"""статистика_сро.py: статистика по всем строительным СРО из выгрузки НОСТРОЙ."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("стат", ROOT / "статистика_сро.py")
стат = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(стат)


def запись(n, номер, start, stop=None, former=False, регион="г. Санкт-Петербург", имя="Объединение строителей СПб"):
    return {"id": n, "inn": f"78{n:08d}", "status": "Исключен" if former else "Является членом",
            "former": former, "sro": f"Ассоциация «{имя}»", "sro_num": номер, "start": start, "stop": stop,
            "name": f"ООО «Компания {n}»", "sro_short": имя, "sro_id": "1", "region": регион}


ЗАПИСИ = [
    запись(1, "СРО-С-003-22042009", "2023-03-10"),
    запись(2, "СРО-С-003-22042009", "2024-05-01", "2025-02-14", former=True),
    запись(3, "СРО-С-003-22042009", "2015-01-01", None, former=True),             # без даты исключения
    запись(4, "СРО-С-003-22042009", "2025-02-20", регион="Ленинградская область"),
    запись(5, "СРО-С-180-20012010", "2025-02-03", регион="г. Москва", имя="МОСК"),
    запись(6, "СРО-С-180-20012010", "2010-01-01", "2023-11-30", former=True, регион="г. Москва", имя="МОСК"),
    запись(1, "СРО-С-003-22042009", "2023-03-10"),                                 # повтор после обрыва
]


class TestСтатистика(unittest.TestCase):
    def _прогнать(self, записи=ЗАПИСИ, состояние=None, лишние=()):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        дамп = Path(tmp.name) / "нострой_реестр.jsonl"
        дамп.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in записи), encoding="utf-8")
        (Path(tmp.name) / "нострой_реестр.jsonl.state.json").write_text(
            json.dumps(состояние or {"готово": True, "всего": 6, "дата": "2026-11-09"}), encoding="utf-8")
        out = Path(tmp.name) / "СРО.xlsx"
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            код = стат.main(["--дамп", str(дамп), "--out", str(out), "--с-года", "2023", *лишние])
        return код, out, err.getvalue()

    def test_сводная(self):
        код, out, _ = self._прогнать()
        self.assertEqual(код, 0)
        ws = load_workbook(out)["Сводная"]
        шапка = [c.value for c in ws[1]]
        self.assertEqual(шапка[:6], ["Рег. номер", "СРО", "Регион", "Всего записей", "Действующих",
                                     "Исключённых (всего)"])
        строки = {r[0]: dict(zip(шапка, r)) for r in ws.iter_rows(min_row=2, values_only=True) if r[0]}
        спб = строки["СРО-С-003-22042009"]
        self.assertEqual((спб["СРО"], спб["Регион"]), ("Объединение строителей СПб", "г. Санкт-Петербург"))
        self.assertEqual((спб["Всего записей"], спб["Действующих"], спб["Исключённых (всего)"]), (4, 2, 2))
        self.assertEqual((спб["Вступило 2023"], спб["Вступило 2024"], спб["Вступило 2025"]), (1, 1, 1))
        self.assertEqual((спб["Исключено 2025"], спб["Без даты искл."]), (1, 1))
        мск = строки["СРО-С-180-20012010"]
        self.assertEqual((мск["Исключено 2023"], мск["Регион"]), (1, "г. Москва"))
        # порядок — по номеру СРО, итог по России — формулами
        self.assertEqual(list(строки)[:2], ["СРО-С-003-22042009", "СРО-С-180-20012010"])
        итог = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[1] == "Итого по России"][0]
        self.assertTrue(str(итог[3]).startswith("=SUM("))

    def test_по_месяцам(self):
        _код, out, _ = self._прогнать()
        ws = load_workbook(out)["Вступления по месяцам"]
        шапка = [c.value for c in ws[1]]
        self.assertEqual(шапка[3], "2023-01")
        сегодня = date.today()
        self.assertEqual(шапка[-1], f"{сегодня.year}-{сегодня.month:02d}")
        спб = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0] == "СРО-С-003-22042009"][0]
        self.assertEqual(спб[шапка.index("2025-02")], 1)
        иск = load_workbook(out)["Исключения по месяцам"]
        ш2 = [c.value for c in иск[1]]
        спб2 = [r for r in иск.iter_rows(min_row=2, values_only=True) if r[0] == "СРО-С-003-22042009"][0]
        self.assertEqual(спб2[ш2.index("2025-02")], 1)

    def test_регионы(self):
        _код, out, _ = self._прогнать()
        ws = load_workbook(out)["По регионам"]
        рег = {r[0]: r for r in ws.iter_rows(min_row=2, values_only=True) if r[0]}
        self.assertEqual(рег["г. Санкт-Петербург"][1:5], (1, 4, 2, 2))
        self.assertEqual(рег["г. Москва"][1:5], (1, 2, 1, 1))

    def test_старая_выгрузка_без_названий(self):
        старые = [{k: v for k, v in r.items() if k not in ("name", "sro_short", "sro_id", "region")}
                  for r in ЗАПИСИ]
        код, _out, err = self._прогнать(старые)
        self.assertEqual(код, 1)
        self.assertIn("--заново", err)

    def test_незаконченная_выгрузка_предупреждает(self):
        _код, _out, err = self._прогнать(состояние={"всего": 100})
        self.assertIn("не закончена", err)
        self.assertIn("неполная", err)

    def test_списки_членов(self):
        _код, out, _ = self._прогнать(лишние=("--с-членами",))
        wb = load_workbook(out.with_name("СРО_члены.xlsx"))
        self.assertEqual(wb.sheetnames, ["С-003-22042009", "С-180-20012010"])
        ws = wb["С-003-22042009"]
        self.assertEqual([c.value for c in ws[1]], ["ИНН", "Название", "Статус", "Дата вступления",
                                                    "Дата исключения"])
        self.assertEqual(ws.max_row, 5)        # 4 члена без повтора


if __name__ == "__main__":
    unittest.main()
