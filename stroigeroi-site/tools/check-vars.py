#!/usr/bin/env python3
"""
Сверяет переменные в шаблонах темы с теми, что отдают контроллеры OpenCart.

Зачем. Twig не ругается на переменную, которой нет: он молча подставляет
пустоту. Ошибка не видна ни в браузере, ни в журнале сервера - просто
пропадает кусок страницы, и узнаёшь об этом от заказчика. Мы на этом уже
попались дважды: в шапке стояли ссылки на сравнение и на товары со скидкой
через имена, которых у движка нет; а `search` в шапке оказался не строкой
запроса, а готовым куском разметки.

Что делает проверка:

  1. читает tools/oc-vars.json - что контроллеры движка кладут в $data
     (снимок исходников OpenCart, пересобирается tools/make-oc-vars.py);
  2. добавляет к нему наши собственные контроллеры из
     opencart-theme/catalog/controller/;
  3. разбирает каждый шаблон темы и находит переменные, которые он читает,
     с учётом локальных имён из {% for %} и {% set %};
  4. ругается на те, которых контроллер не отдаёт.

Отдельно, уже без ругани, печатает обратное: переменные, которые контроллер
отдаёт, а шаблон не показывает. Целиком этот список читать бессмысленно
(в нём все неиспользованные text_*), поэтому в него попадают только те,
чьё отсутствие видно посетителю: сообщения об ошибках, капча, области
для модулей.

    python3 tools/check-vars.py

Выход 1 - есть чего чинить.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = ROOT / 'opencart-theme/catalog/view/theme/stroigeroi2026/template'
OURS = ROOT / 'opencart-theme/catalog/controller'
VARS = ROOT / 'tools/oc-vars.json'

# Шаблон рисуется контроллером того же имени - кроме двух случаев:
# common/success.twig показывает checkout/success (своего контроллера
# у этого шаблона нет, его выводят чужие), а account/order_list.twig -
# контроллер account/order (у него два шаблона: список и заказ).
ROUTE_OF = {'common/success': 'checkout/success', 'account/order_list': 'account/order'}

# Имена, которые Twig понимает сам: ключевые слова, литералы, счётчик цикла.
KEYWORDS = set('''
and or not in is if else elseif endif for endfor set endset block endblock
macro endmacro import from as include with only extends embed endembed
filter endfilter apply endapply autoescape endautoescape spaceless do flush
verbatim endverbatim use deprecated sandbox trans endtrans
true false none null defined empty even odd iterable same starts ends
matches divisible by constant ignore missing loop
'''.split())

# Переменные, отсутствие которых на странице заметно посетителю.
# Только по ним имеет смысл обратная проверка.
VISIBLE = re.compile(r'^(error|success|warning|attention|captcha)')
SLOTS = {'content_top', 'content_bottom', 'column_left', 'column_right',
         'pagination', 'results', 'breadcrumbs', 'header', 'footer'}

# Не показываем нарочно - с причиной. Всё остальное, что контроллер отдаёт,
# а шаблон не выводит, проверка назовёт вслух: молча пропавший модуль
# или несработавшая проверка формы выглядят одинаково - никак.
SILENT = {
    'column_left': 'боковая колонка есть только у списков товаров',
    'column_right': 'правой колонки в этой вёрстке нет вовсе',
}
SILENT_AT = {
    'account/order': {
        'success': 'сообщение после «Повторить заказ» - его показывает страница заказа '
                   '(order_info, стандартная тема), а не список',
        'error_warning': 'то же для ошибки «Повторить заказ»: контроллер кладёт её '
                         'только в info(), в список она не приходит',
    },
    'information/contact': {
        'captcha': 'форма уходит в наш information/callback, не в стоковый',
        'error_name': 'то же: поля проверяет наш обработчик',
        'error_email': 'почту форма не спрашивает - только телефон',
        'error_enquiry': 'то же: поля проверяет наш обработчик',
    },
    'product/product': {
        'captcha': 'отзывов на сайте нет - показывать нечего',
        'pagination': 'листалка отзывов; её рисует product/review.twig',
        'results': 'счётчик отзывов; там же',
    },
}

# Строки языкового файла движок кладёт в данные шаблона сам (событие
# event/language в OpenCart 3), в $data контроллера их нет. Перечислены
# поимённо и с причиной, а не все text_* подряд: иначе проверка перестала
# бы ловить опечатки в именах.
LANGUAGE = {
    'error/not_found': {
        'heading_title': 'заголовок из языкового файла; у пустой корзины - из checkout/cart',
        'text_error': 'текст из языкового файла; пустой корзине checkout/cart кладёт text_empty',
    },
}

STRING = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", re.S)
TAG = re.compile(r'{#.*?#}|{{(.*?)}}|{%-?(.*?)-?%}', re.S)
NAME = re.compile(r'(?<![\w.])([A-Za-z_]\w*)')
FOR = re.compile(r'^\s*for\s+(.+?)\s+in\s+(.+?)$', re.S)
SET = re.compile(r'^\s*set\s+([\w\s,]+?)(?:=(.*))?$', re.S)
MACRO = re.compile(r'^\s*macro\s+\w+\s*\((.*?)\)\s*$', re.S)
# «Я знаю, что переменной может не быть»: |default(...) и is defined.
GUARD = re.compile(r'([A-Za-z_]\w*)\s*\|\s*default\(|'
                   r'([A-Za-z_]\w*)\s+is\s+(?:not\s+)?defined')


def php_vars(path):
    """Имена из $data['...'] в контроллере."""
    src = path.read_text(encoding='utf-8', errors='replace')
    return set(re.findall(r"\$data\['([a-z_0-9]+)'\]", src))


def used(text):
    """Переменные, которые шаблон читает у контроллера.

    Локальные имена - из {% for %}, {% set %} и аргументов {% macro %} -
    в счёт не идут: их шаблон объявляет сам. Область видимости считается
    честно, стопкой: имя из цикла живёт до {% endfor %} и не дальше.
    """
    guarded = {m.group(1) or m.group(2) for m in GUARD.finditer(text)}
    scopes = [set()]
    seen = {}

    def read(expr, where):
        expr = STRING.sub(' ', expr)
        for m in NAME.finditer(expr):
            name, end = m.group(1), m.end()
            tail = expr[end:]
            head = expr[:m.start()]
            if name in KEYWORDS:
                continue
            if tail.lstrip().startswith('('):       # вызов функции
                continue
            if tail.lstrip().startswith('=') and not tail.lstrip().startswith('=='):
                continue                            # именованный аргумент
            if head.rstrip().endswith('|'):         # фильтр
                continue
            if re.search(r'\bis\s+(not\s+)?$', head):  # тест
                continue
            if any(name in s for s in scopes):      # локальное имя
                continue
            seen.setdefault(name, where)
        return expr

    for m in TAG.finditer(text):
        line = text.count('\n', 0, m.start()) + 1
        if m.group(1) is not None:                  # {{ ... }}
            read(m.group(1), line)
            continue
        if m.group(2) is None:                      # {# ... #}
            continue
        body = m.group(2)
        word = body.strip().split(' ')[0].strip()
        if word == 'for':
            f = FOR.match(body)
            if f:
                names = [n.strip() for n in f.group(1).split(',')]
                rest = f.group(2)
                cond = ''
                if re.search(r'\sif\s', rest):
                    rest, cond = re.split(r'\sif\s', rest, 1)
                read(rest, line)
                scopes.append({n for n in names if n} | {'loop'})
                if cond:
                    read(cond, line)
            continue
        if word == 'endfor' or word == 'endmacro':
            if len(scopes) > 1:
                scopes.pop()
            continue
        if word == 'set':
            s = SET.match(body)
            if s:
                if s.group(2):
                    read(s.group(2), line)
                for n in s.group(1).split(','):
                    if n.strip():
                        scopes[-1].add(n.strip())
            continue
        if word == 'macro':
            mm = MACRO.match(body)
            args = {a.strip().split('=')[0].strip()
                    for a in (mm.group(1).split(',') if mm else [])}
            scopes.append({a for a in args if a})
            continue
        read(body, line)

    return {n: w for n, w in seen.items() if n not in guarded}


def main():
    known = json.loads(VARS.read_text(encoding='utf-8'))
    known.pop('__', None)
    for php in sorted(OURS.rglob('*.php')):
        route = php.relative_to(OURS).with_suffix('').as_posix()
        known.setdefault(route, [])
        known[route] = sorted(set(known[route]) | php_vars(php))

    bad = []
    quiet = []
    noroute = []

    for tpl in sorted(TPL.rglob('*.twig')):
        name = tpl.relative_to(TPL).with_suffix('').as_posix()
        route = ROUTE_OF.get(name, name)
        if route not in known:
            noroute.append(name)
            continue
        gives = set(known[route]) | set(LANGUAGE.get(route, {}))
        takes = used(tpl.read_text(encoding='utf-8'))
        for var, line in sorted(takes.items()):
            if var not in gives:
                bad.append((name, line, var, route))
        for var in sorted(gives - set(takes)):
            if not (VISIBLE.match(var) or var in SLOTS):
                continue
            if var in SILENT or var in SILENT_AT.get(route, {}):
                continue
            quiet.append((name, var))

    if noroute:
        print('Шаблоны без контроллера (сверить не с чем):')
        for n in noroute:
            print(f'  {n}.twig')
        print()

    if quiet:
        print('Контроллер отдаёт, шаблон не показывает:')
        for name, var in quiet:
            print(f'  {name}.twig: {var}')
        print('Если так и задумано - впишите причину в SILENT_AT '
              'в этом же файле.')
        print()

    if bad:
        print('Шаблон читает переменную, которой контроллер не отдаёт:')
        for name, line, var, route in bad:
            print(f'  {name}.twig:{line}: {var}  (нет в {route})')
        print()
        print(f'Всего: {len(bad)}. Twig подставит на их месте пустоту молча.')
        return 1

    print(f'Проверено шаблонов: {len(list(TPL.rglob("*.twig")))}. '
          'Несуществующих переменных нет.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
