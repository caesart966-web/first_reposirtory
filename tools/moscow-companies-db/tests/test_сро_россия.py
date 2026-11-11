"""сро_россия.py: таблица по всем СРО — строительные плюс проектные и изыскательские."""

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("сро_россия", ROOT / "сро_россия.py")
россия = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(россия)


def сводки(tmp: Path) -> tuple[Path, Path]:
    спб = json.loads((ROOT / "spb_2026_11" / "сводка.json").read_text(encoding="utf-8"))
    мск = json.loads((ROOT / "msk_2026_11" / "сводка.json").read_text(encoding="utf-8"))
    строит = dict(мск, сро=спб["сро"] + мск["сро"] + [
        {"рег_номер": "СРО-С-999-01012020", "id": 999, "ошибка": "HTTP 503",
         "карточка": {"город": "Казань", "состояние": "enabled"}}])
    # подставные НОПРИЗ: в Москве проектная и изыскательская, в Петербурге — только проектная,
    # в Казани — проектная, в Москве ещё недействующая изыскательская
    образец = мск["сро"][0]
    def сро(номер, город, инн, состояние="enabled"):
        x = copy.deepcopy(образец)
        x.update(рег_номер=номер, id=hash(номер) % 10000, инн=инн, краткое_название=f"Ассоциация «{номер}»")
        x["карточка"] = dict(x["карточка"], город=город, состояние=состояние)
        return x
    ноприз = dict(мск, сро=[сро("СРО-П-001-01012009", "Москва", "7700000001"),
                            сро("СРО-И-001-01012009", "г. Москва", "7700000002"),
                            сро("СРО-П-002-01012009", "Санкт-Петербург", "7800000001"),
                            сро("СРО-П-003-01012009", "Казань", "1600000001"),
                            сро("СРО-И-002-01012009", "Москва", "7700000003", "disabled")])
    a, b = tmp / "нострой.json", tmp / "ноприз.json"
    a.write_text(json.dumps(строит, ensure_ascii=False), encoding="utf-8")
    b.write_text(json.dumps(ноприз, ensure_ascii=False), encoding="utf-8")
    return a, b


class TestРоссия(unittest.TestCase):
    def test_таблица(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a, b = сводки(tmp)
            with redirect_stdout(io.StringIO()):
                россия.main(["--нострой", str(a), "--ноприз", str(b), "--out", str(tmp / "р.xlsx")])
            wb = openpyxl.load_workbook(tmp / "р.xlsx")
        self.assertEqual(wb.sheetnames[:3], ["Сводная", "Регионы", "Проектные и изыскательские"])
        # Сводная: 19 СРО Петербурга + 56 действующих Москвы, у каждой — П и И в её регионе
        ws = wb["Сводная"]
        шапка = [c.value for c in ws[1]]
        строки = [dict(zip(шапка, [c.value for c in r])) for r in ws.iter_rows(min_row=2)]
        сро = [r for r in строки if r["Рег. номер"] and isinstance(r["Всего записей"], int)]
        self.assertEqual(len(сро), 75)
        мск = next(r for r in сро if r["Рег. номер"] == "СРО-С-018-16072009")
        self.assertEqual((мск["Регион"], мск["Проектных СРО в регионе"], мск["Изыскательских СРО в регионе"]),
                         ("г. Москва", 1, 1))
        спб = next(r for r in сро if r["Рег. номер"] == "СРО-С-003-22042009")
        self.assertEqual((спб["Регион"], спб["Проектных СРО в регионе"], спб["Изыскательских СРО в регионе"]),
                         ("г. Санкт-Петербург", 1, 0))
        self.assertTrue(any(r["СРО"] == "Итого по 75 СРО" for r in строки))
        # Регионы: Москва — все три вида, Петербург — нет, Казань — только проектная
        wr = wb["Регионы"]
        рег = {r[0]: r for r in wr.iter_rows(min_row=2, values_only=True) if r[0] and not str(r[0]).startswith("Итого")}
        self.assertEqual(рег["г. Москва"][1], 56)
        self.assertEqual(рег["г. Москва"][7], "да")
        self.assertEqual(рег["г. Санкт-Петербург"][7], "нет")
        self.assertEqual((рег["Республика Татарстан"][1], рег["Республика Татарстан"][3]), (0, 1))
        # недействующая изыскательская в Москве в счёт не идёт, а на своём листе есть
        wm = wb["Недействующие СРО"]
        номера = [r[0] for r in wm.iter_rows(min_row=2, values_only=True) if r[0] and isinstance(r[4], int)]
        self.assertIn("СРО-И-002-01012009", номера)
        self.assertEqual(len(номера), 46)                               # 45 Москвы + 1
        wp = wb["Проектные и изыскательские"]
        self.assertEqual([r[2] for r in wp.iter_rows(min_row=2, max_row=5, values_only=True)],
                         ["Изыскательская", "Проектная", "Проектная", "Проектная"])
        # несобранная СРО видна на «Как считали»
        как = " ".join(str(c.value) for r in wb["Как считали"].iter_rows() for c in r)
        self.assertIn("СРО-С-999-01012020", как)

    def test_динамика(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a, b = сводки(tmp)
            with redirect_stdout(io.StringIO()):
                россия.main(["--нострой", str(a), "--ноприз", str(b), "--out", str(tmp / "р.xlsx")])
            wd = openpyxl.load_workbook(tmp / "р.xlsx")["Динамика по России"]
        self.assertEqual([c.value for c in wd[1]][:5], ["Строительные: вступления", "2023", "2024", "2025", "2026"])
        self.assertIsNone(wd.cell(13, 5).value)                         # декабрь 2026 ещё не наступил
        self.assertEqual(len(wd._charts), 2)


if __name__ == "__main__":
    unittest.main()
