import re, sys, pathlib
OPEN = {'for':'endfor','if':'endif','block':'endblock','set':'endset','macro':'endmacro','spaceless':'endspaceless','verbatim':'endverbatim'}
CLOSE = set(OPEN.values())
bad = 0
for f in sorted(pathlib.Path(sys.argv[1]).rglob('*.twig')):
    raw = f.read_text(encoding='utf-8')
    # Фигурные скобки javascript не имеют отношения к Twig: в шапке
    # есть '}}catch' и '{}})();', и по ним проверка ругалась на чистый файл.
    s = re.sub(r'<script>.*?</script>', '', raw, flags=re.S)
    # {% set x = ... %} — однострочный, не открывает блок
    stack, line = [], 1
    for m in re.finditer(r'\{%-?\s*(\w+)(.*?)-?%\}', s, re.S):
        line = s.count('\n', 0, m.start()) + 1
        tag, rest = m.group(1), m.group(2)
        if tag == 'set' and '=' in rest:
            continue
        if tag in OPEN:
            stack.append((tag, line))
        elif tag in CLOSE:
            if not stack:
                print(f'{f}:{line}: лишний {{% {tag} %}}'); bad += 1
            elif OPEN[stack[-1][0]] != tag:
                print(f'{f}:{line}: {{% {tag} %}} закрывает {{% {stack[-1][0]} %}} со строки {stack[-1][1]}'); bad += 1; stack.pop()
            else:
                stack.pop()
    # Переменные, в которых движок отдаёт УЖЕ ОТРИСОВАННУЮ разметку,
    # а не строку. Подставленные внутрь атрибута, они разрывают тег:
    # в value="{{ search }}" приходит целая форма поиска, половина
    # разметки вываливается на страницу текстом, и ни Twig, ни движок
    # об этом не сообщают. Ровно на этом мы и обожглись на живом сайте.
    #
    # Списка два, и это важно. Одни и те же имена означают разное
    # в разных местах: в шапке cart и search - отрисованные блоки,
    # а в карте сайта и на страницах каталога это просто адреса ссылок.
    # Один общий список давал ложные тревоги на наших же файлах.
    RENDERED_ANYWHERE = ('header', 'footer', 'column_left', 'column_right',
                         'content_top', 'content_bottom', 'pagination',
                         'captcha', 'modules')
    RENDERED_IN_HEADER = ('cart', 'search', 'menu', 'language', 'currency')

    risky = RENDERED_ANYWHERE
    if f.name == 'header.twig':
        risky = RENDERED_ANYWHERE + RENDERED_IN_HEADER

    for m in re.finditer(r'[\w-]+="[^"]*\{\{\s*(\w+)[^}]*\}\}[^"]*"', raw):
        if m.group(1) in risky:
            line = raw.count('\n', 0, m.start()) + 1
            print(f'{f}:{line}: {{{{ {m.group(1)} }}}} внутри атрибута — '
                  f'там приходит разметка, а не строка'); bad += 1

    # Ссылки на страницы макета. В теме таких быть не может: страниц
    # с именами вроде catalog.html на сайте нет, а браузер о битой ссылке
    # молчит - человек просто попадает в никуда. Ловим здесь, а не глазами.
    for href in set(re.findall(r'href="([^"]*\.html[^"]*)"', raw)):
        print(f'{f}: ссылка на страницу макета — {href}'); bad += 1

    # Пометки Яндекса «не индексировать»: <!--noindex--> ... <!--/noindex-->
    # или <noindex> ... </noindex>. Незакрытая пометка молча выключает из
    # индекса всё, что ниже неё, - почти всю страницу, а на странице её
    # не видно. Вложенные Яндекс учитывает только до первой закрывающей.
    # Комментарии Twig вычеркнуты: в них пометки упоминаются словами.
    depth = 0
    for closing in re.findall(r'<(?:!--\s*)?(/?)noindex\s*(?:--)?>',
                              re.sub(r'\{#.*?#\}', '', raw, flags=re.S), re.I):
        depth += -1 if closing else 1
        if depth not in (0, 1):
            print(f'{f}: пометки noindex вложены или закрыты лишний раз'); bad += 1
            break
    else:
        if depth:
            print(f'{f}: пометка noindex не закрыта — Яндекс не проиндексирует всё, что ниже неё'); bad += 1

    for m in re.finditer(r'<script>(.*?)</script>', raw, re.S):
        if '{{' in m.group(1) or '{%' in m.group(1):
            print(f'{f}: теги Twig внутри <script> - так делать нельзя'); bad += 1
    for tag, ln in stack:
        print(f'{f}:{ln}: не закрыт {{% {tag} %}}'); bad += 1
    # незакрытые {{ }}
    if s.count('{{') != s.count('}}'):
        print(f'{f}: разное число {{{{ и }}}}'); bad += 1
    if s.count('{%') != s.count('%}'):
        print(f'{f}: разное число {{% и %}}'); bad += 1
    if s.count('{#') != s.count('#}'):
        print(f'{f}: разное число {{# и #}}'); bad += 1
    print(f'  ok  {f.name}  ({len(raw.splitlines())} строк)')

# --- Договор темы с движком -------------------------------------------------
# Шапка обязана подключать библиотеки движка ДО петли со скриптами
# расширений. Своей вёрстке они не нужны - весь наш javascript обходится
# без библиотек, - но на них рассчитывает всё, что ставится расширениями.
#
# Мы на этом уже попались: jQuery в шапке не было, и simple.js,
# simplecheckout.js, live_search.js и файлы OCFilter падали на первой
# строке - молча, ещё до того как что-нибудь связать с кнопками.
# На оформлении заказа не работали «+», «−», «Обновить» и «Подтвердить
# заказ»: заказ с сайта было не оформить вообще. Из разметки этого
# не видно, в журналах сервера тоже - ошибка живёт только в браузере.
header = pathlib.Path(sys.argv[1], 'catalog/view/theme/stroigeroi2026/template/common/header.twig')
if header.exists():
    src = header.read_text(encoding='utf-8')
    loop = src.find('{% for script in scripts %}')
    for lib, why in (('jquery', 'на нём написаны все расширения'),
                     ('common.js', 'в нём $.fn.autocomplete для живого поиска и объект cart')):
        at = src.find(lib)
        if at < 0:
            print(f'header.twig: не подключён {lib} — {why}'); bad += 1
        elif loop >= 0 and at > loop:
            print(f'header.twig: {lib} подключается ПОСЛЕ скриптов расширений — '
                  f'им он нужен раньше'); bad += 1

sys.exit(1 if bad else 0)
