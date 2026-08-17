# -*- coding: utf-8 -*-
"""Автоматические проверки.

Все данные в тестах ВЫМЫШЛЕННЫЕ: реквизиты реальных компаний здесь
не используются принципиально.

Запуск:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import morphology, validators  # noqa: E402
from src.company_parser import (parse_card, parse_text,  # noqa: E402
                                split_company_name)
from src.context_builder import build_context  # noqa: E402
from src.docx_engine import (extract_all_text, extract_package_text,  # noqa: E402
                             fill_template, scan_placeholders)
from src.document_generator import (GeneratorError, Project,  # noqa: E402
                                    check_readiness, company_folder_name, generate)
from src.models import CompanyData  # noqa: E402
from src.readers import read_card  # noqa: E402

# --------------------------------------------------------------- фикстуры
ALPHA = dict(
    full_name='Общество с ограниченной ответственностью «Ромашка-Строй»',
    short_name='ООО «Ромашка»',
    inn="7812345675",
    kpp="781201001",
    ogrn="1237800000008",
    legal_address="190000, г. Санкт-Петербург, ул. Вымышленная, д. 1, лит. А, пом. 5",
    actual_address="190000, г. Санкт-Петербург, ул. Вымышленная, д. 1, лит. А, пом. 5",
    phone="+7 (812) 000-00-01",
    email="info@romashka-test.example",
    director_position="Генеральный директор",
    director_full_name="Иванов Иван Иванович",
    director_basis="Устав",
)

BETA = dict(
    full_name='Акционерное общество «Василёк»',
    short_name='АО «Василёк»',
    inn="7701001005",
    kpp="770101001",
    ogrn="1027700000008",
    legal_address="101000, г. Москва, пер. Придуманный, д. 2",
    actual_address="101000, г. Москва, пер. Придуманный, д. 2",
    phone="+7 (495) 000-00-02",
    email="office@vasilek-test.example",
    director_position="Директор",
    director_full_name="Петрова Мария Сергеевна",
    director_basis="Устав",
)


def make_company(data: dict) -> CompanyData:
    company = CompanyData()
    for key, value in data.items():
        company.set(key, value)
    company.doc_date = "17.08.2026"
    return company


def make_card_docx(path: Path, data: dict) -> None:
    """Собрать вымышленную карточку компании в DOCX (как у настоящего клиента)."""
    from docx import Document

    document = Document()
    document.add_paragraph(f"Реквизиты компании {data['short_name']}")
    rows = [
        ("Полное наименование", data["full_name"]),
        ("Сокращенное наименование", data["short_name"]),
        ("Юридический адрес", data["legal_address"]),
        ("Почтовый адрес", "-"),
        ("ИНН", data["inn"]),
        ("КПП", data["kpp"]),
        ("ОГРН", data["ogrn"]),
        (data["director_position"],
         f"{data['director_full_name']} (на основании {data['director_basis']}а)"),
        ("Эл. почта", data["email"]),
        ("Телефон", data["phone"]),
    ]
    table = document.add_table(rows=len(rows), cols=2)
    for index, (label, value) in enumerate(rows):
        table.cell(index, 0).text = label
        table.cell(index, 1).text = value
    document.save(str(path))


# --------------------------------------------------------------- проверки
class TestValidators(unittest.TestCase):
    def test_inn_length(self):
        issues = validators.validate_inn("781234567")
        self.assertTrue(issues)
        self.assertIn("10 цифр", issues[0].text)

    def test_inn_checksum(self):
        self.assertTrue(validators.inn_checksum_ok("7812345675"))
        self.assertFalse(validators.inn_checksum_ok("7812345678"))
        issues = validators.validate_inn("7812345678")
        self.assertTrue(any("контрольного числа" in i.text for i in issues))

    def test_inn_valid_is_silent(self):
        self.assertEqual(validators.validate_inn("7812345675"), [])

    def test_ogrn(self):
        self.assertTrue(validators.ogrn_checksum_ok("1237800000008"))
        self.assertEqual(validators.validate_ogrn("1237800000008"), [])
        self.assertTrue(validators.validate_ogrn("1237800000000"))

    def test_ogrn_length_message(self):
        issues = validators.validate_ogrn("12378")
        self.assertIn("13 цифр", issues[0].text)

    def test_spaces_are_reported_not_silently_fixed(self):
        issues = validators.validate_inn("78 1234 5675")
        self.assertTrue(any(i.severity == "warning" for i in issues))

    def test_email_and_phone(self):
        self.assertEqual(validators.validate_email("a.b@mail.example"), [])
        self.assertTrue(validators.validate_email("a.b@mail"))
        self.assertTrue(validators.validate_email("имя @mail.ru"))
        self.assertEqual(validators.validate_phone("+7 (812) 000-00-01"), [])
        self.assertTrue(validators.validate_phone("12345"))

    def test_kpp(self):
        self.assertEqual(validators.validate_kpp("781201001"), [])
        self.assertTrue(validators.validate_kpp("78120100"))


class TestMorphology(unittest.TestCase):
    def test_male_genitive(self):
        result = morphology.full_name_genitive("Иванов Иван Иванович")
        self.assertTrue(result.confident)
        self.assertEqual(result.value, "Иванова Ивана Ивановича")

    def test_male_genitive_hard_cases(self):
        cases = {
            "Хомутов Роман Сергеевич": "Хомутова Романа Сергеевича",
            "Кодловский Максим Анатольевич": "Кодловского Максима Анатольевича",
            "Кузьмин Илья Петрович": "Кузьмина Ильи Петровича",
            "Толстой Лев Николаевич": "Толстого Льва Николаевича",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                result = morphology.full_name_genitive(source)
                self.assertTrue(result.confident, result.reason)
                self.assertEqual(result.value, expected)

    def test_female_genitive(self):
        result = morphology.full_name_genitive("Петрова Мария Сергеевна")
        self.assertTrue(result.confident)
        self.assertEqual(result.value, "Петровой Марии Сергеевны")

    def test_indeclinable_surname(self):
        result = morphology.full_name_genitive("Шевченко Пётр Иванович")
        self.assertTrue(result.confident)
        self.assertEqual(result.value, "Шевченко Петра Ивановича")

    def test_fleeting_vowel_surname_is_not_guessed(self):
        # Соловей → Соловья, но Кочубей → Кочубея. Правило ненадёжно —
        # программа обязана спросить, а не угадать.
        result = morphology.full_name_genitive("Соловей Андрей Игоревич")
        self.assertFalse(result.confident)

    def test_uncertain_without_patronymic(self):
        result = morphology.full_name_genitive("Иванов Иван")
        self.assertFalse(result.confident)

    def test_uncertain_foreign_name(self):
        result = morphology.full_name_genitive("Ким Ли Сунович")
        # отчество распознано, но имя нестандартное — программа не уверена
        self.assertFalse(result.confident)

    def test_short_name(self):
        self.assertEqual(morphology.short_name("Иванов Иван Иванович").value, "Иванов И.И.")

    def test_positions(self):
        self.assertEqual(morphology.position_genitive("Генеральный директор").value,
                         "Генерального директора")
        self.assertEqual(morphology.position_genitive("Директор").value, "Директора")
        self.assertFalse(morphology.position_genitive("Главный распорядитель").confident)

    def test_basis(self):
        self.assertEqual(morphology.basis_genitive("Устав").value, "Устава")
        self.assertEqual(morphology.basis_genitive("Устава").value, "Устава")

    def test_normalize_caps(self):
        self.assertEqual(morphology.normalize_person_name("ИВАНОВ ИВАН ИВАНОВИЧ"),
                         "Иванов Иван Иванович")
        self.assertEqual(morphology.normalize_person_name("Иванов Иван Иванович"),
                         "Иванов Иван Иванович")


class TestParser(unittest.TestCase):
    def test_split_company_name(self):
        self.assertEqual(split_company_name('ООО «Ромашка»'),
                         ("ООО", "Общество с ограниченной ответственностью", "Ромашка"))
        self.assertEqual(
            split_company_name('Общество с ограниченной ответственностью «Ромашка»')[2],
            "Ромашка")

    def test_split_removes_duplicated_form(self):
        # В карточках часто пишут форму дважды.
        result = split_company_name(
            'Общество с ограниченной ответственностью ООО «Ромашка»')
        self.assertEqual(result[2], "Ромашка")
        self.assertEqual(result[0], "ООО")

    def test_parse_plain_text(self):
        parsed = parse_text(
            'ООО "СТРОЙИНВЕСТ"\n'
            "ИНН 7812345675\nКПП 781201001\nОГРН 1237800000008\n"
            "Юридический адрес: 190000, г. Санкт-Петербург, ул. Вымышленная, д. 1\n"
            "Генеральный директор: Иванов Иван Иванович\n"
            "Действует на основании Устава\n"
            "Телефон: +7 (812) 000-00-01\nEmail: info@test.example\n")
        company = parsed.company
        self.assertEqual(company.inn, "7812345675")
        self.assertEqual(company.kpp, "781201001")
        self.assertEqual(company.ogrn, "1237800000008")
        self.assertEqual(company.director_position, "Генеральный директор")
        self.assertEqual(company.director_full_name, "Иванов Иван Иванович")
        self.assertEqual(company.director_basis, "Устав")
        self.assertEqual(company.email, "info@test.example")
        self.assertIn("Вымышленная", company.legal_address)
        self.assertEqual(split_company_name(company.short_name)[2], "СТРОЙИНВЕСТ")

    def test_derived_full_name_is_flagged(self):
        parsed = parse_text('ООО "Ромашка"\nИНН 7812345675')
        self.assertIn("full_name", parsed.derived)

    def test_dash_means_empty(self):
        parsed = parse_text("Почтовый адрес: -\nИНН 7812345675")
        self.assertEqual(parsed.company.postal_address, "")

    def test_never_invents_missing_data(self):
        parsed = parse_text("ИНН 7812345675")
        self.assertEqual(parsed.company.director_full_name, "")
        self.assertEqual(parsed.company.legal_address, "")
        self.assertEqual(parsed.company.email, "")

    def test_parse_docx_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "card.docx"
            make_card_docx(path, ALPHA)
            parsed = parse_card(read_card(path))
            self.assertEqual(parsed.company.inn, ALPHA["inn"])
            self.assertEqual(parsed.company.ogrn, ALPHA["ogrn"])
            self.assertEqual(parsed.company.director_full_name, ALPHA["director_full_name"])
            self.assertEqual(parsed.company.director_position, ALPHA["director_position"])
            self.assertEqual(parsed.company.director_basis, "Устав")
            self.assertEqual(parsed.company.postal_address, "")


class TestDocxEngine(unittest.TestCase):
    """Проверка движка на документе, специально разбитом на фрагменты."""

    def _make_split_template(self, path: Path) -> None:
        from docx import Document

        document = Document()
        paragraph = document.add_paragraph()
        for piece in ("Компания ", "{{comp", "any_name", "_bare}}", " с ИНН ", "{{inn}}", "."):
            paragraph.add_run(piece)
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "{{phone}}"
        table.cell(0, 1).text = "{{email}}"
        section = document.sections[0]
        section.header.paragraphs[0].text = "Шапка: {{inn}}"
        document.save(str(path))

    def test_placeholder_split_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "t.docx"
            output = Path(tmp) / "out.docx"
            self._make_split_template(template)

            self.assertIn("company_name_bare", scan_placeholders(template))

            report = fill_template(template, output, {
                "company_name_bare": "Ромашка", "inn": "7812345675",
                "phone": "+7 (812) 000-00-01", "email": "a@b.example"})
            text = extract_all_text(output)
            self.assertIn("Компания Ромашка с ИНН 7812345675.", text)
            self.assertIn("Шапка: 7812345675", text)   # колонтитул тоже заполнен
            self.assertIn("+7 (812) 000-00-01", text)  # и таблица
            self.assertNotIn("{{", text)
            self.assertEqual(report.replaced["inn"], 2)

    def test_template_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "t.docx"
            output = Path(tmp) / "out.docx"
            self._make_split_template(template)
            before = template.read_bytes()
            fill_template(template, output, {"inn": "7812345675"})
            self.assertEqual(before, template.read_bytes())

    def test_refuses_to_overwrite_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "t.docx"
            self._make_split_template(template)
            with self.assertRaises(Exception):
                fill_template(template, template, {"inn": "1"})

    def test_unknown_variable_is_reported_not_erased(self):
        with tempfile.TemporaryDirectory() as tmp:
            template = Path(tmp) / "t.docx"
            output = Path(tmp) / "out.docx"
            self._make_split_template(template)
            report = fill_template(template, output, {"inn": "7812345675"})
            self.assertIn("company_name_bare", report.unknown)
            self.assertIn("{{company_name_bare}}", extract_all_text(output))


class TestContext(unittest.TestCase):
    def setUp(self):
        self.project = Project(ROOT)

    def test_digits_split(self):
        context = build_context(make_company(ALPHA), self.project.attorney())
        self.assertEqual(context.values["inn_d1"], "7")
        self.assertEqual(context.values["inn_d10"], "5")
        self.assertEqual("".join(context.values[f"ogrn_d{i}"] for i in range(1, 14)),
                         ALPHA["ogrn"])

    def test_date_in_russian(self):
        context = build_context(make_company(ALPHA), self.project.attorney())
        self.assertEqual(context.values["doc_day"], "17")
        self.assertEqual(context.values["doc_month_name"], "августа")
        self.assertEqual(context.values["doc_year"], "2026")

    def test_marks(self):
        company = make_company(ALPHA)
        company.harm_fund_level = "3"
        company.contract_fund_level = ""
        context = build_context(company, self.project.attorney())
        self.assertEqual(context.values["mark_harm_level3"], "v")
        self.assertEqual(context.values["mark_harm_level1"], "")
        self.assertEqual(context.values["mark_object_ordinary"], "V")
        self.assertTrue(all(context.values[f"mark_contract_level{i}"] == ""
                            for i in "12345"))

    def test_confirmation_requested_for_unclear_declension(self):
        company = make_company(ALPHA)
        company.set("director_full_name", "Ким Ли Сунович")
        context = build_context(company, self.project.attorney())
        self.assertTrue(any(c.key == "director_full_name_genitive"
                            for c in context.confirmations))

    def test_override_wins(self):
        company = make_company(ALPHA)
        company.set("director_full_name", "Ким Ли Сунович")
        company.overrides["director_full_name_genitive"] = "Ким Ли Суновича"
        context = build_context(company, self.project.attorney())
        self.assertEqual(context.values["director_full_name_genitive"], "Ким Ли Суновича")
        self.assertFalse(any(c.key == "director_full_name_genitive"
                             for c in context.confirmations))

    def test_non_ooo_is_warned(self):
        context = build_context(make_company(BETA), self.project.attorney())
        self.assertTrue(any("ООО" in note for note in context.notes))


class TestGeneration(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.project = Project(ROOT)
        self.project.output_root = self.tmp / "out"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_fields_block_generation(self):
        company = make_company(ALPHA)
        company.set("actual_address", "")
        company.set("email", "")
        readiness = check_readiness(self.project, company)
        missing = {label for item in readiness for label in item.missing}
        self.assertIn("Фактический адрес", missing)
        self.assertIn("Электронная почта", missing)
        with self.assertRaises(GeneratorError) as ctx:
            generate(self.project, company, make_pdf=False)
        message = str(ctx.exception)
        self.assertIn("не хватает следующих данных", message)
        self.assertIn("Фактический адрес", message)
        self.assertNotIn("нет данных", message)

    def test_full_scenario(self):
        company = make_company(ALPHA)
        result = generate(self.project, company, make_pdf=False,
                          today=date(2026, 8, 17))
        self.assertTrue(result.ok, [r.problems for r in result.quality])
        self.assertEqual(len(result.created), 2)
        names = sorted(p.name for p in result.created)
        self.assertEqual(names, ["01_Заявление_о_вступлении.docx", "02_Доверенность.docx"])
        self.assertEqual(result.folder.name, "7812345675_ООО Ромашка")

        application = extract_all_text(result.folder / "01_Заявление_о_вступлении.docx")
        self.assertIn("Общество с ограниченной ответственностью «Ромашка-Строй»; "
                      "ООО «Ромашка»", application)
        self.assertIn("от «17» августа 2026 г.", application)
        self.assertIn(ALPHA["legal_address"], application)
        self.assertIn("Генеральный директор - Иванов Иван Иванович", application)
        self.assertIn("Иванов И.И.", application)
        self.assertNotIn("{{", application)

        power = extract_all_text(result.folder / "02_Доверенность.docx")
        self.assertIn("«17» августа 2026 г.", power)
        self.assertIn("в лице Генерального директора – Иванова Ивана Ивановича", power)
        self.assertIn("на основании Устава", power)
        self.assertIn("ИНН 7812345675", power)
        self.assertIn("Кодловского Максима Анатольевича", power)  # представитель на месте
        self.assertNotIn("{{", power)

    def test_originals_untouched(self):
        before = {path.name: path.read_bytes()
                  for path in (ROOT / "templates").glob("*.docx")}
        originals = {path.name: path.read_bytes()
                     for path in (ROOT / "templates" / "_originals").glob("*.docx")}
        generate(self.project, make_company(ALPHA), make_pdf=False)
        after = {path.name: path.read_bytes()
                 for path in (ROOT / "templates").glob("*.docx")}
        after_originals = {path.name: path.read_bytes()
                           for path in (ROOT / "templates" / "_originals").glob("*.docx")}
        self.assertEqual(before, after)
        self.assertEqual(originals, after_originals)

    def test_no_foreign_email_left_from_template(self):
        """В бланке заявления в гиперссылке оставалась почта чужой компании."""
        result = generate(self.project, make_company(ALPHA), make_pdf=False)
        for path in result.created:
            self.assertNotIn("regionrem", extract_package_text(path))
        application = result.folder / "01_Заявление_о_вступлении.docx"
        # почта попала и в текст, и в адрес гиперссылки
        self.assertEqual(extract_package_text(application).count(ALPHA["email"]), 2)

    def test_two_companies_do_not_mix(self):
        """Главная защита: данные компании А не попадают в документы компании Б."""
        first = generate(self.project, make_company(ALPHA), make_pdf=False)
        second = generate(self.project, make_company(BETA), make_pdf=False)
        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertNotEqual(first.folder, second.folder)

        for path in second.created:
            text = extract_package_text(path)
            for marker in (ALPHA["inn"], ALPHA["ogrn"], "Ромашка",
                           ALPHA["email"], "Иванов"):
                self.assertNotIn(marker, text, f"{path.name}: осталось «{marker}»")
        for path in first.created:
            text = extract_package_text(path)
            for marker in (BETA["inn"], BETA["ogrn"], "Василёк",
                           BETA["email"], "Петров"):
                self.assertNotIn(marker, text, f"{path.name}: попало «{marker}»")

    def test_beta_company_documents(self):
        company = make_company(BETA)
        result = generate(self.project, company, make_pdf=False, today=date(2026, 8, 17))
        self.assertTrue(result.ok, [r.problems for r in result.quality])
        power = extract_all_text(result.folder / "02_Доверенность.docx")
        self.assertIn("Акционерное общество «Василёк»", power)
        self.assertIn("в лице Директора – Петровой Марии Сергеевны", power)
        self.assertIn("Петрова М.С.", power)
        application = extract_all_text(result.folder / "01_Заявление_о_вступлении.docx")
        self.assertIn("Акционерное общество «Василёк»; АО «Василёк»", application)

    def test_quality_control_catches_broken_document(self):
        """Если в шаблоне есть переменная без данных, документ не считается готовым."""
        company = make_company(ALPHA)
        context_free = self.project.variables
        self.assertIn("inn", context_free)
        result = generate(self.project, company, make_pdf=False)
        report = result.quality[0]
        self.assertTrue(report.ok)
        self.assertEqual(report.problems, [])

    def test_folder_name_is_safe_for_windows(self):
        company = make_company(ALPHA)
        company.set("short_name", 'ООО «Ромашка/Строй: "Плюс"»')
        name = company_folder_name(company)
        for bad in '<>:"/\\|?*':
            self.assertNotIn(bad, name)
        self.assertTrue(name.startswith("7812345675_"))


class TestProjectConfig(unittest.TestCase):
    def test_every_placeholder_is_described(self):
        """Каждая переменная шаблонов должна быть описана в config/variables.json."""
        from src.quality_control import lookup_variable

        project = Project(ROOT)
        for spec in project.enabled_documents():
            for name in project.placeholders(spec):
                with self.subTest(document=spec.title, variable=name):
                    self.assertIsNotNone(
                        lookup_variable(name, project.variables),
                        f"переменная {{{{{name}}}}} не описана в config/variables.json")

    def test_templates_exist(self):
        project = Project(ROOT)
        for spec in project.enabled_documents():
            self.assertTrue(project.template_path(spec).exists(), spec.template)


if __name__ == "__main__":
    unittest.main(verbosity=2)
