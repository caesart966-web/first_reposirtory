#!/usr/bin/env python3
"""
Создаёт недостающие страницы макета из общей оболочки.

Зачем скриптом, а не руками: шапка, подвал и модальные окна физически
повторяются в каждом html-файле (в теме OpenCart они станут одним
header.twig, но пока это статика). Написанная руками страница почти
наверняка разойдётся с остальными — где-то отстанет пункт меню,
где-то потеряется атрибут. Скрипт берёт готовую страницу как оболочку
и меняет в ней только заголовки и содержимое <main>.

Запускается один раз при добавлении страницы:
    python3 tools/make-pages.py

Дальше страницы живут как обычные файлы: их правят руками, а скрипт
второй раз не запускают — он перезапишет правки. Поэтому он и лежит
в tools/, а не в сборке.
"""

import re
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent
SHELL = DIR / '404.html'
OG_BASE = 'https://caesart966-web.github.io/first_reposirtory/stroigeroi/'


def shell_parts():
    html = SHELL.read_text(encoding='utf-8')
    head_end = html.index('<main id="main">')
    tail_start = html.index('</main>')
    return html[:head_end], html[tail_start:]


def make(name, title, description, main, breadcrumb):
    """breadcrumb — список пар (текст, ссылка); последняя без ссылки."""
    head, tail = shell_parts()

    head = re.sub(r'<title>[^<]*</title>', f'<title>{title} | Строй-Герой</title>', head)
    head = re.sub(r'(name="description" content=")[^"]*"', rf'\g<1>{description}"', head)
    head = re.sub(r'(rel="canonical" href=")[^"]*"', rf'\g<1>{name}.html"', head)
    head = re.sub(r'(property="og:title" content=")[^"]*"', rf'\g<1>{title} | Строй-Герой"', head)
    head = re.sub(r'(property="og:description" content=")[^"]*"', rf'\g<1>{description}"', head)
    head = re.sub(r'(property="og:url" content=")[^"]*"', rf'\g<1>{OG_BASE}{name}.html"', head)

    crumbs = ''.join(
        f'<li><a href="{href}">{text}</a></li>' if href else f'<li aria-current="page">{text}</li>'
        for text, href in breadcrumb
    )
    nav = (
        '\n    <nav class="breadcrumbs" aria-label="Хлебные крошки">\n'
        f'      <ol>{crumbs}</ol>\n'
        '    </nav>\n'
    ) if breadcrumb else ''

    body = f'<main id="main">\n  <div class="container">\n{nav}{main}\n  </div>\n'
    (DIR / f'{name}.html').write_text(head + body + tail, encoding='utf-8')
    return name


# ==========================================================================
#  Содержимое страниц. Данных заказчика здесь нет — только пустые места.
# ==========================================================================

CHECKOUT = '''
    <div class="page-head">
      <h1>Оформление заказа</h1>
      <p>Заполните контакты и выберите, как забрать заказ. Менеджер перезвонит и подтвердит наличие.</p>
    </div>

    <div class="steps">
      <span class="step"><a href="cart.html"><span class="step__num">1</span> Корзина</a></span>
      <span class="step is-current"><span class="step__num">2</span> Контакты</span>
      <span class="step is-current"><span class="step__num">3</span> Получение</span>
      <span class="step"><span class="step__num">4</span> Готово</span>
    </div>

    <div class="data-notice">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M12 11.5v5M12 8h.01"/></svg>
      <p><strong>Так выглядит оформление.</strong> Заказ из макета никуда не уходит — принимать его пока некому.</p>
    </div>

    <form class="checkout" data-validate novalidate>
      <div class="checkout__main">

        <section class="checkout-block">
          <h2 class="subhead">Контакты</h2>
          <div class="form__row">
            <label for="co-name">Как вас зовут</label>
            <input id="co-name" name="name" type="text" placeholder="Имя" required>
            <p class="form__error">Впишите имя</p>
          </div>
          <div class="form__row">
            <label for="co-phone">Телефон</label>
            <input id="co-phone" name="phone" type="tel" placeholder="+7 (___) ___-__-__" data-phone-mask required>
            <p class="form__error">Впишите номер телефона</p>
          </div>
          <div class="form__row">
            <label for="co-comment">Комментарий к заказу</label>
            <textarea id="co-comment" name="comment" rows="3" placeholder="Например: нужен длинномер, привезти до обеда"></textarea>
          </div>
        </section>

        <section class="checkout-block">
          <h2 class="subhead">Как забрать</h2>
          <div class="pickup">
            <label class="pickup__option">
              <input type="radio" name="pickup" value="self" checked>
              <span class="pickup__body">
                <strong>Самовывоз из магазина</strong>
                <span class="note">Три точки: Чубарова 16 к.40, 50 лет Октября 17А, Елизово, Магистральная 2/2</span>
              </span>
            </label>
            <label class="pickup__option">
              <input type="radio" name="pickup" value="delivery">
              <span class="pickup__body">
                <strong>Доставка</strong>
                <span class="ph ph--inline">зоны, сроки и стоимость — от заказчика</span>
              </span>
            </label>
          </div>

          <div class="form__row gap-md">
            <label for="co-shop">Магазин для самовывоза</label>
            <select id="co-shop" class="select" name="shop">
              <option>ул. Чубарова, 16, корп. 40 — Петропавловск-Камчатский</option>
              <option>просп. 50 лет Октября, 17А — Петропавловск-Камчатский</option>
              <option>Магистральная ул., 2/2 — Елизово</option>
            </select>
          </div>
        </section>

        <section class="checkout-block">
          <h2 class="subhead">Оплата</h2>
          <p class="ph">Способы оплаты, работа с юрлицами и порядок расчёта — нужны от заказчика.</p>
        </section>

      </div>

      <aside class="cart-total checkout__side">
        <h2 class="cart-total__title">Ваш заказ</h2>
        <div class="cart-total__row"><span>Товары</span> <span class="ph ph--inline">сумма</span></div>
        <div class="cart-total__row"><span>Доставка</span> <span class="ph ph--inline">нужны условия</span></div>
        <div class="cart-total__row cart-total__row--sum"><span>К оплате</span> <span class="ph ph--inline">сумма</span></div>

        <label class="consent gap-md">
          <input type="checkbox" required>
          <span>Согласен на обработку персональных данных и с <a href="policy.html">политикой конфиденциальности</a></span>
          <p class="form__error">Без согласия отправить нельзя</p>
        </label>

        <button class="btn btn--action btn--block btn--lg gap-ms" type="submit">Подтвердить заказ</button>
        <p class="calc__hint">Проверка полей работает по-настоящему: попробуйте отправить пустую форму.</p>
      </aside>
    </form>
'''

ORDER_DONE = '''
    <div class="steps">
      <span class="step"><a href="cart.html"><span class="step__num">1</span> Корзина</a></span>
      <span class="step"><span class="step__num">2</span> Контакты</span>
      <span class="step"><span class="step__num">3</span> Получение</span>
      <span class="step is-current"><span class="step__num">4</span> Готово</span>
    </div>

    <div class="error-page">
      <p class="error-page__code error-page__code--ok">✓</p>
      <h1>Заказ принят</h1>
      <p class="error-page__text">Номер заказа <span class="ph ph--inline">из учётной системы</span>. Менеджер перезвонит, подтвердит наличие и назовёт время.</p>

      <div class="error-page__actions row-actions">
        <a class="btn btn--action btn--lg" href="catalog.html">Продолжить покупки</a>
        <a class="btn btn--outline btn--lg" href="tel:+79638300999">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M5 4h4l2 5-2.5 1.5a12 12 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1Z"/></svg>
          8-963-830-09-99
        </a>
      </div>

      <div class="data-notice gap-xl">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M12 11.5v5M12 8h.01"/></svg>
        <p><strong>Так выглядит последний шаг.</strong> Номер заказа и письмо на почту появятся, когда сайт подключат к учётной системе.</p>
      </div>
    </div>
'''

FAVOURITES = '''
    <div class="page-head">
      <h1>Избранное</h1>
      <p>Отложенные товары. Список хранится в этом браузере и не пропадёт при переходе между страницами.</p>
    </div>

    <div class="empty-state">
      <span class="empty-state__icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20s-7-4.35-7-9.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 7 3.5c0 5.15-7 9.5-7 9.5Z"/></svg>
      </span>
      <h2 class="block-title">Пока пусто</h2>
      <p class="note-measure">Нажмите на сердечко в карточке товара — он появится здесь. В макете счётчик избранного растёт, но сами карточки сюда не переносятся: переносить пока нечего, прайса нет.</p>
      <div class="row-actions">
        <a class="btn btn--action" href="catalog.html">Перейти в каталог</a>
      </div>
    </div>
'''

COMPARE = '''
    <div class="page-head">
      <h1>Сравнение</h1>
      <p>Характеристики выбранных товаров рядом, столбец к столбцу.</p>
    </div>

    <div class="data-notice">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M12 11.5v5M12 8h.01"/></svg>
      <p><strong>Так выглядит сравнение.</strong> Строки таблицы — характеристики из прайса: их состав задаёт заказчик.</p>
    </div>

    <div class="table-scroll">
      <table class="compare-table">
        <caption class="visually-hidden">Сравнение выбранных товаров</caption>
        <thead>
          <tr>
            <th scope="col">Характеристика</th>
            <th scope="col"><span class="ph ph--inline">товар 1</span></th>
            <th scope="col"><span class="ph ph--inline">товар 2</span></th>
            <th scope="col"><span class="ph ph--inline">товар 3</span></th>
          </tr>
        </thead>
        <tbody>
          <tr><th scope="row">Цена</th><td><span class="ph ph--inline">цена, ₽</span></td><td><span class="ph ph--inline">цена, ₽</span></td><td><span class="ph ph--inline">цена, ₽</span></td></tr>
          <tr><th scope="row">Артикул</th><td><span class="ph ph--inline">из прайса</span></td><td><span class="ph ph--inline">из прайса</span></td><td><span class="ph ph--inline">из прайса</span></td></tr>
          <tr><th scope="row">Бренд</th><td><span class="ph ph--inline">из прайса</span></td><td><span class="ph ph--inline">из прайса</span></td><td><span class="ph ph--inline">из прайса</span></td></tr>
          <tr><th scope="row">Фасовка</th><td><span class="ph ph--inline">из прайса</span></td><td><span class="ph ph--inline">из прайса</span></td><td><span class="ph ph--inline">из прайса</span></td></tr>
          <tr><th scope="row">Остаток</th><td><span class="ph ph--inline">из учётной системы</span></td><td><span class="ph ph--inline">из учётной системы</span></td><td><span class="ph ph--inline">из учётной системы</span></td></tr>
        </tbody>
      </table>
    </div>

    <div class="row-actions">
      <a class="btn btn--outline" href="catalog.html">Добавить ещё товар</a>
    </div>
'''

LOGIN = '''
    <div class="page-head">
      <h1>Вход</h1>
      <p>Личный кабинет нужен, чтобы видеть свои заказы и повторять их одним нажатием.</p>
    </div>

    <div class="auth">
      <form class="form auth__form" data-validate novalidate>
        <h2 class="subhead">Войти по телефону</h2>
        <div class="form__row">
          <label for="li-phone">Телефон</label>
          <input id="li-phone" name="phone" type="tel" placeholder="+7 (___) ___-__-__" data-phone-mask required>
          <p class="form__error">Впишите номер телефона</p>
        </div>
        <button class="btn btn--action btn--block btn--lg" type="submit">Получить код</button>
        <p class="calc__hint">В макете код не приходит: отправлять его пока нечем.</p>
      </form>

      <aside class="auth__side">
        <h2 class="subhead">Зачем кабинет</h2>
        <ul class="checklist">
          <li>История заказов и повтор в одно нажатие</li>
          <li>Сохранённые адреса доставки</li>
          <li><span class="ph ph--inline">условия для юрлиц — от заказчика</span></li>
          <li><span class="ph ph--inline">накопительная скидка — от заказчика</span></li>
        </ul>
        <p class="note gap-md">Нет аккаунта? Он заведётся сам при первом заказе — отдельная регистрация не нужна.</p>
      </aside>
    </div>
'''

TERMS = '''
    <div class="page-head">
      <h1>Пользовательское соглашение</h1>
      <p>Правила, на которых магазин и покупатель пользуются сайтом.</p>
    </div>

    <div class="data-notice">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M12 11.5v5M12 8h.01"/></svg>
      <p><strong>Текст нужен от заказчика.</strong> Как и политику, это готовит юрист под конкретное юрлицо и порядок работы магазина — сочинять такое мы не беремся.</p>
    </div>

    <div class="prose">
      <h2 class="subhead">Что должно быть в документе</h2>
      <ul class="checklist">
        <li>Кто владелец сайта: полное название, ИНН, ОГРН, адрес</li>
        <li>Что считается заказом и в какой момент он принят</li>
        <li>Цены на сайте: справочные или публичная оферта</li>
        <li>Что делать, если товара не оказалось в наличии</li>
        <li>Сроки и порядок отмены заказа покупателем</li>
        <li>Кто отвечает за ошибки в описаниях и фотографиях</li>
        <li>Как решаются споры и в каком суде</li>
      </ul>

      <h2 class="subhead gap-xl">Куда этот текст встанет</h2>
      <p class="ph">Здесь — полный текст соглашения от заказчика. Сюда же ведёт ссылка из подвала и из формы оформления заказа.</p>

      <h2 class="subhead gap-xl">Чем отличается от политики</h2>
      <p>Политика обработки данных отвечает на вопрос «что вы делаете с моим телефоном» и обязательна по закону. Соглашение отвечает на вопрос «по каким правилам мы торгуем» и защищает магазин в спорных ситуациях. Документы разные, нужны оба.</p>
      <p class="note">Оба текста берутся у юриста. Мы размечаем страницы и ставим ссылки, чтобы ничего не потерялось.</p>
    </div>
'''

POLICY = '''
    <div class="page-head">
      <h1>Политика обработки персональных данных</h1>
      <p>Страница обязательна: на сайте есть формы, значит он собирает персональные данные.</p>
    </div>

    <div class="data-notice">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M12 11.5v5M12 8h.01"/></svg>
      <p><strong>Текст нужен от заказчика.</strong> Юридический документ мы не сочиняем — его готовит юрист под конкретное юрлицо и состав собираемых данных.</p>
    </div>

    <div class="prose">
      <h2 class="subhead">Что должно быть в документе</h2>
      <ul class="checklist">
        <li>Кто оператор: полное название, ИНН, ОГРН, адрес</li>
        <li>Какие данные собираются: имя, телефон, почта из форм заявки и заказа</li>
        <li>Зачем: обработка заказа, обратный звонок, доставка</li>
        <li>Сколько хранятся и как удаляются</li>
        <li>Кому передаются: служба доставки, платёжный сервис</li>
        <li>Как отозвать согласие и куда написать</li>
      </ul>

      <h2 class="subhead gap-xl">Куда этот текст встанет</h2>
      <p class="ph">Здесь — полный текст политики от заказчика. Сюда же ведут ссылки из форм, плашки cookie и подвала.</p>

      <h2 class="subhead gap-xl">Что ещё нужно, кроме этой страницы</h2>
      <ul class="checklist">
        <li>Уведомление в Роскомнадзор о том, что вы оператор персональных данных</li>
        <li>Галочка согласия в каждой форме — в макете она уже стоит</li>
        <li>Хостинг на территории России</li>
      </ul>
      <p class="note">Сроки и суммы штрафов уточняйте у юриста: правила по персональным данным меняются часто.</p>
    </div>
'''

PAGES = [
    ('checkout', 'Оформление заказа', 'Контакты, способ получения и оплата.', CHECKOUT,
     [('Главная', 'index.html'), ('Корзина', 'cart.html'), ('Оформление', None)]),
    ('order-done', 'Заказ принят', 'Заказ принят, менеджер перезвонит.', ORDER_DONE,
     [('Главная', 'index.html'), ('Корзина', 'cart.html'), ('Заказ принят', None)]),
    ('favourites', 'Избранное', 'Отложенные товары.', FAVOURITES,
     [('Главная', 'index.html'), ('Избранное', None)]),
    ('compare', 'Сравнение', 'Характеристики выбранных товаров рядом.', COMPARE,
     [('Главная', 'index.html'), ('Сравнение', None)]),
    ('login', 'Вход', 'Личный кабинет: заказы и повтор покупки.', LOGIN,
     [('Главная', 'index.html'), ('Вход', None)]),
    ('policy', 'Политика обработки персональных данных', 'Как магазин обращается с персональными данными.', POLICY,
     [('Главная', 'index.html'), ('Политика', None)]),
    ('terms', 'Пользовательское соглашение', 'Правила пользования сайтом магазина.', TERMS,
     [('Главная', 'index.html'), ('Соглашение', None)]),
]

if __name__ == '__main__':
    """Без аргументов скрипт НИЧЕГО не делает — и это намеренно.

    Он перезаписывает страницу целиком, а созданные страницы дальше живут
    своей жизнью: в них появляются ссылки, атрибуты, неразрывные пробелы
    от сборщика. Запуск «за компанию» стирает всё это молча. Так уже
    случилось однажды: при добавлении соглашения скрипт заодно перезаписал
    шесть готовых страниц, и оформление заказа перестало вести на «заказ
    принят».

    Поэтому имя страницы теперь обязательный аргумент:
        python3 tools/make-pages.py terms
    """
    known = {name: args for args in PAGES for name in [args[0]]}
    wanted = [a for a in sys.argv[1:] if not a.startswith('-')]

    if not wanted:
        print('Укажите, какую страницу создать. Скрипт перезаписывает файл целиком,')
        print('поэтому «создать все» отдельной командой не предусмотрено.\n')
        print('Доступные:', ', '.join(known))
        print('Пример:    python3 tools/make-pages.py terms')
        sys.exit(1)

    unknown = [w for w in wanted if w not in known]
    if unknown:
        print('Не знаю таких страниц:', ', '.join(unknown))
        print('Доступные:', ', '.join(known))
        sys.exit(1)

    for name in wanted:
        target = DIR / f'{name}.html'
        if target.exists() and '--force' not in sys.argv:
            print(f'{name}.html уже есть. Перезаписать — только с --force,')
            print('и учтите: правки, сделанные после создания, пропадут.')
            sys.exit(1)
        print('создана', make(*known[name]) + '.html')

    print('\nДальше: добавить в список PAGES в build.mjs и запустить node build.mjs')
