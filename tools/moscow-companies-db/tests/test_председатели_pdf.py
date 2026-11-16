import importlib.util
import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

_ПУТЬ = Path(__file__).resolve().parent.parent / "председатели_pdf.py"
_spec = importlib.util.spec_from_file_location("председатели_pdf", _ПУТЬ)
д = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(д)

_ШРИФТ = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def pdf(*листы: str) -> bytes:
    """PDF с текстом (пустая строка — лист без текста, как скан)."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except ImportError as e:
        raise unittest.SkipTest("нет reportlab") from e
    if not os.path.exists(_ШРИФТ):
        raise unittest.SkipTest("нет шрифта DejaVu")
    pdfmetrics.registerFont(TTFont("DejaVu", _ШРИФТ))
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for лист in листы:
        if лист:
            c.setFont("DejaVu", 11)
            for i, строка in enumerate(лист.split("\n")):
                c.drawString(40, 800 - 16 * i, строка)
        else:
            c.rect(40, 400, 300, 300, fill=1)     # «картинка» без текста
        c.showPage()
    c.save()
    return buf.getvalue()


def docx(текст: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        абзацы = "".join(f"<w:p><w:r><w:t>{с}</w:t></w:r></w:p>" for с in текст.split("\n"))
        z.writestr("word/document.xml", f'<w:document xmlns:w="x"><w:body>{абзацы}</w:body></w:document>')
    return buf.getvalue()


class Падежи(unittest.TestCase):
    def test_полное_имя(self):
        for было, стало in [
            (("Иванова", "Ивана", "Ивановича"), "Иванов Иван Иванович"),
            (("Петровскую", "Марию", "Сергеевну"), "Петровская Мария Сергеевна"),
            (("Мельника", "Павла", "Андреевича"), "Мельник Павел Андреевич"),
            (("Сидоровой", "Ольги", "Петровны"), "Сидорова Ольга Петровна"),
            (("Шевченко", "Дмитрия", "Юрьевича"), "Шевченко Дмитрий Юрьевич"),
            (("Кузнецову", "Наталью", "Викторовну"), "Кузнецова Наталья Викторовна"),
            (("Коваля", "Игоря", "Николаевича"), "Коваль Игорь Николаевич"),
            (("Ивановым", "Сергеем", "Петровичем"), "Иванов Сергей Петрович"),
            (("Белых", "Анну", "Ильиничну"), "Белых Анна Ильинична"),
            (("Иванов", "Иван", "Иванович"), "Иванов Иван Иванович"),
        ]:
            self.assertEqual(д.именительный(*было), стало)

    def test_инициалы(self):
        self.assertEqual(д.фамилия_при_инициалах("Иванова", "вин"), "Иванов")
        self.assertEqual(д.фамилия_при_инициалах("Иванову", "вин"), "Иванова")
        self.assertEqual(д.фамилия_при_инициалах("Иванова", "им"), "Иванова")
        self.assertEqual(д.фамилия_при_инициалах("Смирнова", "род"), "Смирнов")


class Протокол(unittest.TestCase):
    def ищи(self, текст):
        н = д.найти_в_документе(текст)
        return н[:2] if н else None

    def test_избрание(self):
        self.assertEqual(self.ищи("РЕШИЛИ: Избрать Председателем Совета Ассоциации Иванова Ивана Ивановича "
                                  "сроком на 5 лет."), (0, "Иванов Иван Иванович"))
        self.assertEqual(self.ищи("Председателем Совета Ассоциации избран Петров Пётр Петрович."),
                         (0, "Петров Пётр Петрович"))
        self.assertEqual(self.ищи("Избрать Сидорову О. П. Председателем Совета Союза."), (0, "Сидорова О. П."))
        self.assertEqual(self.ищи("Избрать Председателем Совета Ассоциации «СРО «Строители Ростова» "
                                  "Морозову Анну Викторовну."), (0, "Морозова Анна Викторовна"))
        self.assertEqual(self.ищи("Избрать членами Совета: Иванова И.И., Петрова П.П.; Председателем Совета "
                                  "из числа членов Совета избрать Петрова П. П."), (0, "Петров П. П."))

    def test_шапка_протокола_совета(self):
        self.assertEqual(self.ищи("Председатель Совета: Кузнецов А. В.\nСекретарь: Иванова Е. Е."),
                         (1, "Кузнецов А. В."))
        self.assertEqual(self.ищи("Председатель Совета ______________ Белов Б. Б."), (1, "Белов Б. Б."))

    def test_упоминание(self):
        self.assertEqual(self.ищи("Слушали доклад Председателя Совета Ассоциации Смирнова С. С. об итогах."),
                         (2, "Смирнов С. С."))

    def test_должность_в_скобках(self):
        self.assertEqual(self.ищи("ПРИСУТСТВОВАЛИ: 1. Будзуляк Богдан Владимирович (председатель Совета "
                                  "Ассоциации) 2. Беляева Валентина Яковлевна 3. Бронников Андрей Николаевич"),
                         (1, "Будзуляк Богдан Владимирович"))

    def test_чужая_организация(self):
        self.assertIsNone(self.ищи("3. Калтайс Валерий Григорьевич – председатель правления ТОООИ «Инстрой»; "
                                   "4. Ефимов Михаил Константинович – генеральный директор"))
        self.assertEqual(self.ищи("Председатель Совета АСРО «РОС ПК» Богомаз Зоя Алексеевна"),
                         (1, "Богомаз Зоя Алексеевна"))

    def test_не_он(self):
        self.assertIsNone(self.ищи("Заместителем председателя Совета избрать Волкова В.В."))
        # председатель собрания — не председатель совета
        self.assertEqual(self.ищи("Избрать председателем общего собрания Козлова К.К. Председатель Совета "
                                  "Орлов О. О. доложил."), (1, "Орлов О. О."))

    def test_дата_и_год(self):
        self.assertEqual(д.дата("Протокол № 15 от 25.04.2024"), (2024, 4, 25))
        self.assertEqual(д.дата("«25» апреля 2024 г. Москва"), (2024, 4, 25))
        self.assertEqual(д.год("Протокол ОС 2023", "/upload/2019/x.pdf"), 2023)

    def test_оценка_ссылки(self):
        self.assertEqual(д.оценка_ссылки("Протокол общего собрания № 12", "/p.pdf"), 0)
        self.assertEqual(д.оценка_ссылки("", "/upload/protokol-obshchego-sobraniya-2022.pdf"), 0)
        self.assertEqual(д.оценка_ссылки("Протокол ОС", "/x.pdf"), 0)
        self.assertEqual(д.оценка_ссылки("Протокол заседания Совета", "/s.pdf"), 2)
        self.assertEqual(д.оценка_ссылки("Устав", "/ustav.pdf"), 5)     # читается последним
        self.assertIsNone(д.оценка_ссылки("Протокол дисциплинарного комитета", "/d.pdf"))


class Документы(unittest.TestCase):
    def test_pdf(self):
        текст, вид = д.текст_документа(pdf("Протокол общего собрания членов Ассоциации\n"
                                           "Избрать Председателем Совета Ассоциации Иванова Ивана Ивановича\n"
                                           "сроком на пять лет. Голосовали: за — единогласно."))
        self.assertEqual(вид, "pdf")
        self.assertEqual(д.найти_в_документе(текст)[1], "Иванов Иван Иванович")

    def test_скан(self):
        self.assertEqual(д.текст_документа(pdf("", ""))[1], "скан")

    def test_docx(self):
        текст, вид = д.текст_документа(docx("Протокол\nПредседателем Совета избрана Орлова Ольга Олеговна"))
        self.assertEqual(вид, "docx")
        self.assertEqual(д.найти_в_документе(текст)[1], "Орлова Ольга Олеговна")

    def test_не_документ(self):
        self.assertEqual(д.текст_документа(b"\x89PNG....")[1], "не прочитан")


class Обход(unittest.TestCase):
    def сайт(self):
        старый = pdf("Протокол № 5 от 20.04.2019\nОбщее собрание членов\n"
                     "Избрать Председателем Совета Ассоциации Старова Степана Сергеевича.\n"
                     + "Обсуждение отчётов.\n" * 3)
        новый = pdf("Протокол № 11 от 18.04.2024\nОбщее собрание членов\n"
                    "Председателем Совета Ассоциации избран Новиков Николай Николаевич.\n"
                    + "Голосовали единогласно.\n" * 3)
        страницы = {
            "http://sro.ru": '<a href="/o-nas/">О нас</a> <a href="/documents/">Документы</a> '
                             '<a href="/news/1">Новость</a>',
            "http://sro.ru/documents/": '<a href="/files/p11.pdf">Протокол общего собрания № 11 (2024)</a>'
                                        '<a href="/files/p5.pdf">Протокол общего собрания № 5 (2019)</a>'
                                        '<a href="/files/scan.pdf">Протокол заседания Совета (скан)</a>'
                                        '<a href="/files/ustav.pdf">Устав</a>',
        }
        файлы = {"http://sro.ru/files/p11.pdf": новый, "http://sro.ru/files/p5.pdf": старый,
                 "http://sro.ru/files/scan.pdf": pdf("")}
        скачано = []

        def скачать(url):
            return (url, страницы[url]) if url in страницы else None

        def скачать_файл(url):
            скачано.append(url)
            return (url, файлы[url]) if url in файлы else None
        return скачать, скачать_файл, скачано

    def test_свежее_избрание(self):
        скачать, скачать_файл, скачано = self.сайт()
        итог = д.обойти("sro.ru", скачать=скачать, скачать_файл=скачать_файл)
        self.assertEqual(итог["Председатель (документ)"], "Новиков Николай Николаевич")
        self.assertEqual(итог[д.ИТОГ], "найдено в документе")
        self.assertEqual(итог["Документ"], "http://sro.ru/files/p11.pdf")
        self.assertEqual(итог["Дата документа"], "18.04.2024")
        self.assertNotIn("http://sro.ru/files/ustav.pdf", скачано)     # устав не качаем
        # протокол 2019 года старше найденного избрания — его не читаем
        self.assertNotIn("http://sro.ru/files/p5.pdf", скачано)

    def test_только_сканы(self):
        def скачать(url):
            return (url, '<a href="/s.pdf">Протокол общего собрания</a>') if url == "http://a.ru" else None
        итог = д.обойти("a.ru", скачать=скачать, скачать_файл=lambda u: (u, pdf("")))
        self.assertEqual(итог[д.ИТОГ], "только сканы — смотреть глазами")
        self.assertEqual(итог["Сканы без текста"], "http://a.ru/s.pdf")

    def test_сайт_не_открылся(self):
        self.assertEqual(д.обойти("a.ru", скачать=lambda u: None, скачать_файл=lambda u: None)[д.ИТОГ],
                         "сайт не открылся")

    def test_файл_дописывается(self):
        from openpyxl import Workbook, load_workbook
        with tempfile.TemporaryDirectory() as tmp:
            путь = Path(tmp) / "п.xlsx"
            wb = Workbook()
            wb.active.append(["Рег. номер", "СРО", "Сайт"])
            wb.active.append(["СРО-С-1", "Тест", "a.ru"])
            wb.save(путь)
            было = д.обойти
            д.обойти = lambda сайт, **_: {д.ИТОГ: "найдено в документе", "Председатель (документ)": "Иванов И. И."}
            try:
                д.main(["--file", str(путь), "--потоков", "1"])
            finally:
                д.обойти = было
            ws = load_workbook(путь).active
            шапка = [c.value for c in ws[1]]
            self.assertIn(д.ИТОГ, шапка)
            self.assertEqual(ws.cell(2, шапка.index("Председатель (документ)") + 1).value, "Иванов И. И.")


class Президент(unittest.TestCase):
    def test_президент_совета(self):
        н = д.найти_в_документе("Президентом Совета Ассоциации избран Иванов Иван Иванович.")
        self.assertEqual(н[:2], (0, "Иванов Иван Иванович"))
        self.assertIsNone(д.найти_в_документе("Вице-президент Совета Петров П. П. доложил."))

    def test_правило_устава(self):
        for т in ["8.3. Президент Ассоциации является Председателем Совета Ассоциации.",
                  "Председатель Совета Ассоциации — Президент Ассоциации.",
                  "Совет Ассоциации возглавляет Президент Ассоциации.",
                  "Президент Ассоциации (единоличный исполнительный орган) по должности является "
                  "председателем Совета"]:
            self.assertIsNotNone(д.президент_во_главе(т), т)
        self.assertIsNone(д.президент_во_главе("Президент Ассоциации является единоличным "
                                                "исполнительным органом Ассоциации."))

    def test_имя_президента(self):
        self.assertEqual(д.имя_президента("Президент Ассоциации Иванов Иван Иванович"), "Иванов Иван Иванович")
        self.assertEqual(д.имя_президента("Президент: Петров П. П."), "Петров П. П.")
        self.assertIsNone(д.имя_президента("Вице-президент Сидоров Сидор Сидорович"))

    def test_оценка_новых_документов(self):
        self.assertEqual(д.оценка_ссылки("Устав Ассоциации", "/ustav.pdf"), 5)
        self.assertEqual(д.оценка_ссылки("Положение о Совете", "/p.pdf"), 5)
        self.assertEqual(д.оценка_ссылки("Отчет о деятельности за 2025 год", "/o.pdf"), 4)
        self.assertEqual(д.оценка_ссылки("Протокол счетной комиссии по избранию Председателя Совета", "/s.pdf"), 2)
        self.assertIsNone(д.оценка_ссылки("Протокол счетной комиссии", "/s.pdf"))


class Сканы(unittest.TestCase):
    def test_сканы_сохраняются_и_распознаются(self):
        скан = pdf("", "")
        страницы = {"http://a.ru": '<a href="/s1.pdf">Протокол общего собрания 2025</a>'
                                   '<a href="/ustav.pdf">Устав</a>'}

        def скачать(url):
            return (url, страницы[url]) if url in страницы else None

        def скачать_файл(url):
            if url.endswith("s1.pdf"):
                return url, скан
            if url.endswith("ustav.pdf"):
                return url, pdf("Устав Ассоциации\nПрезидент Ассоциации является Председателем Совета "
                                "Ассоциации.\n" + "Общие положения устава. " * 10)
            return None
        with tempfile.TemporaryDirectory() as tmp:
            итог = д.обойти("a.ru", скачать=скачать, скачать_файл=скачать_файл, папка_сканов=Path(tmp) / "a")
            self.assertEqual(итог["Сканы без текста"], "http://a.ru/s1.pdf")
            файл = итог["Сканы (файлы)"]
            self.assertTrue(Path(файл).exists())
            self.assertIn("совет возглавляет президент", итог[д.ИТОГ])
            self.assertIn("является Председателем Совета", итог["Совет возглавляет президент"])
            z = dict(итог)
            нашёл = д.из_сканов(z, lambda картинка: "Протокол № 7 от 15.04.2025\nПредседателем Совета "
                                                   "Ассоциации избран Сканов Сергей Сергеевич.")
            self.assertTrue(нашёл)
            self.assertEqual(z["Председатель (документ)"], "Сканов Сергей Сергеевич")
            self.assertEqual(z["Документ"], "http://a.ru/s1.pdf")
            self.assertEqual(z["Дата документа"], "15.04.2025")
            self.assertEqual(z[д.ИТОГ], "найдено в скане")

    def test_только_распознать(self):
        from openpyxl import Workbook, load_workbook
        with tempfile.TemporaryDirectory() as tmp:
            скан = Path(tmp) / "1.pdf"
            скан.write_bytes(pdf(""))
            путь = Path(tmp) / "п.xlsx"
            wb = Workbook()
            wb.active.append(["Рег. номер", "Сайт", д.ИТОГ, "Сканы без текста", "Сканы (файлы)"])
            wb.active.append(["СРО-С-1", "a.ru", "только сканы — смотреть глазами", "http://a.ru/1.pdf", str(скан)])
            wb.save(путь)
            было = д.распознаватель
            д.распознаватель = lambda: ((lambda к: "Председатель Совета: Сканов С. С."), "тест")
            try:
                д.main(["--file", str(путь), "--только-распознать"])
            finally:
                д.распознаватель = было
            ws = load_workbook(путь).active
            шапка = [c.value for c in ws[1]]
            self.assertEqual(ws.cell(2, шапка.index("Председатель (документ)") + 1).value, "Сканов С. С.")
            self.assertTrue(str(ws.cell(2, шапка.index(д.ИТОГ) + 1).value).startswith("найдено в скане"))


if __name__ == "__main__":
    unittest.main()
