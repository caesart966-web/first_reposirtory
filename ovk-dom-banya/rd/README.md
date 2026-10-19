# РД ОВиК И05.09.26-ОВ (дом и баня) — исходники (черновик, в работе)

- `rdbase.py`, `rd_sheet.py`, `rd_stamp.py`, `underlay.py`, `render_layout.py` — общая библиотека листов
  (DXF: модель в мм от осей 1/А, листы — пространство листа с видовыми экранами; PDF — render_layout.py).
- `sheets/*.py` — по скрипту на лист (состав — `SHEET_LIST` в rdbase.py).
- `calc/` — расчётная основа РД (`calc_rd.py` → `rd_calc.json`, отчёт `rd_calc.md`), черновая спецификация,
  решения Заказчика (`decisions.md`).
- Подложка — выгрузка АР из Revit (19.10.2026), DXF после dwg2dxf лежат вне репозитория.
- DWG собирает робот `.github/workflows/dwg-convert-ovk.yml` из `cad/ovk-i05-09-26/dxf`.
