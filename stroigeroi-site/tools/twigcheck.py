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
    RENDERED = ('header', 'footer', 'menu', 'cart', 'search', 'language',
                'currency', 'column_left', 'column_right', 'content_top',
                'content_bottom', 'pagination', 'captcha', 'modules')
    # Исключение: в СОБСТВЕННОМ шаблоне модуля переменная означает данные,
    # а не разметку. В common/cart.twig переменная cart - адрес корзины,
    # в common/search.twig переменная search - текст запроса. Разметку
    # они получают снаружи, в шапке, и опасно там, а не здесь.
    for m in re.finditer(r'[\w-]+="[^"]*\{\{\s*(\w+)[^}]*\}\}[^"]*"', raw):
        if m.group(1) in RENDERED and m.group(1) != f.stem:
            line = raw.count('\n', 0, m.start()) + 1
            print(f'{f}:{line}: {{{{ {m.group(1)} }}}} внутри атрибута — '
                  f'там приходит разметка, а не строка'); bad += 1

    # Ссылки на страницы макета. В теме таких быть не может: страниц
    # с именами вроде catalog.html на сайте нет, а браузер о битой ссылке
    # молчит - человек просто попадает в никуда. Ловим здесь, а не глазами.
    for href in set(re.findall(r'href="([^"]*\.html[^"]*)"', raw)):
        print(f'{f}: ссылка на страницу макета — {href}'); bad += 1

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
sys.exit(1 if bad else 0)
