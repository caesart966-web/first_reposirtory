# РД ОВиК И05.09.26-ОВ (дом и баня) — исходники (черновик, в работе)

- `rdbase.py`, `rd_sheet.py`, `rd_stamp.py`, `underlay.py`, `render_layout.py` — общая библиотека листов
  (DXF: модель в мм от осей 1/А, листы — пространство листа с видовыми экранами; PDF — render_layout.py).
- `sheets/*.py` — по скрипту на лист (состав — `SHEET_LIST` в rdbase.py).
- `calc/` — расчётная основа РД (`calc_rd.py` → `rd_calc.json`, отчёт `rd_calc.md`), черновая спецификация,
  решения Заказчика (`decisions.md`).
- Подложка — выгрузка АР из Revit (19.10.2026), DXF после dwg2dxf лежат вне репозитория.
- DWG собирает робот `.github/workflows/dwg-convert-ovk.yml` из `cad/ovk-i05-09-26/dxf`.

## 3D-модель вентиляции и кондиционирования (22.10.2026)

- `model3d.py` — модель по тем же данным, что листы 9–12 (`ov_vent1`, `ov_vent2`, `ov_vent_schemes`, `ov_bath`; баня — по ГП01): трассы,
  сечения, расходы; высоты — по зонам подшивки; пересечения разводятся обходом по высоте (таблица на листе 11,
  фасонные части — в СО). Стены — штриховки стен АР03/АР09. Выход в `out/3d/`: `model.json`,
  `I05-09-26-OV-3D.dxf` (мм, начало — оси 1/А, сети — POLYFACE; DWG собирает робот),
  `I05-09-26-OV-3D.ifc` (IFC4, координаты выгрузки Revit: оси 1/А = 2168; 4673 мм), `razvodka.txt`.
- `viewer3d/` — просмотрщик в одном HTML (three.js r169, без интернета): `npm install`, затем
  `node build.mjs ../out/3d/model.json ../out/3d/view.html`; снимки видов — `node shot.mjs view.html папка вид?view=iso&ui=0`,
  PDF видов — `python3 views_pdf.py папка выход.pdf`.
