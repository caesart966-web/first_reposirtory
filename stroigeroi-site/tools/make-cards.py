#!/usr/bin/env python3
"""
Собирает разметку товарной карточки темы stroigeroi2026.

Карточка нужна в шести местах: четыре товарных модуля, страница раздела,
страница поиска. Разметка у них одна, и если править её руками в шести
файлах, они разойдутся - вопрос лишь в том, на какой правке.

Модули featured, bestseller, latest и special отдают шаблону один и тот же
набор данных: heading_title и products. Разметка карусели у них тоже одна.
Поэтому четыре файла порождаются из одного образца - руками они бы
разошлись при первой же правке карточки.

Правите разметку здесь и запускаете:

    python3 tools/make-cards.py

Модули порождаются целиком. В остальные шаблоны карточка вставляется
между метками:

    {# КАРТОЧКА: начало - собирается tools/make-cards.py, руками не править #}
    {# КАРТОЧКА: конец #}

Файл без меток скрипт не трогает. Файл с меткой начала, но без конца -
это ошибка, и скрипт об этом говорит, а не молча портит шаблон.

Карточка товара повторяет разметку макета. Отличия от макета - по делу:

  - фотография настоящая (product.thumb); если у товара её нет, движок
    сам подставляет заглушку no_image, поэтому пустого места не будет;
  - у кнопок стоит data-product-id: по нему app.js понимает, что работает
    с настоящей корзиной движка, а не с памятью браузера;
  - цена со скидкой выводится второй строкой, зачёркнутой - в макете
    такого не было, потому что цен не было вовсе;
  - артикула, фасовки и остатка НЕТ: движок в модулях их не отдаёт.
    Пустые пунктирные плашки макета сюда переносить нельзя - на живом
    сайте они читались бы как поломка, а не как "данные будут".
"""
import pathlib
import sys

THEME = 'stroigeroi2026'
OUT = pathlib.Path('opencart-theme/catalog/view/theme') / THEME / 'template' / 'extension' / 'module'

ICON_PREV = '<svg class="icon-prev" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="m6 9 6 6 6-6"/></svg>'
ICON_NEXT = ICON_PREV.replace('icon-prev', 'icon-next')
ICON_FAV = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 20s-7-4.4-7-9.4A3.9 3.9 0 0 1 12 7.2 3.9 3.9 0 0 1 19 10.6c0 5-7 9.4-7 9.4Z"/></svg>'
ICON_CMP = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M6 20V11M12 20V4M18 20v-6"/></svg>'
ICON_CART = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="9.5" cy="19.5" r="1.6"/><circle cx="17" cy="19.5" r="1.6"/><path d="M3 4h2l2.4 11.2a1 1 0 0 0 1 .8h8.6a1 1 0 0 0 1-.8L20 8H6"/></svg>'

CARD = """          <article class="product-card reveal">
            <div class="product-card__media">
              {% if product.special %}<div class="product-card__badges"><span class="badge badge--sale">Скидка</span></div>{% endif %}
              <a class="product-card__photo" href="{{ product.href }}"><img src="{{ product.thumb }}" alt="{{ product.name }}" loading="lazy" decoding="async"></a>
              <div class="product-card__tools">
                <button class="card-tool" type="button" data-add="fav" data-product-id="{{ product.product_id }}" aria-label="В избранное">""" + ICON_FAV + """</button>
                <button class="card-tool" type="button" data-add="compare" data-product-id="{{ product.product_id }}" aria-label="К сравнению">""" + ICON_CMP + """</button>
              </div>
            </div>
            <div class="product-card__body">
              <a class="product-card__title" href="{{ product.href }}">{{ product.name }}</a>
            </div>
            <div class="product-card__bottom">
              {% if product.special %}<span class="price">{{ product.special }}</span><s class="price-old">{{ product.price }}</s>{% else %}<span class="price">{{ product.price }}</span>{% endif %}
              <button class="btn btn--action product-card__buy" type="button" data-add="cart" data-product-id="{{ product.product_id }}" aria-label="В корзину">""" + ICON_CART + """<span>В корзину</span></button>
            </div>
          </article>
"""

BODY = """{#
  СГЕНЕРИРОВАННЫЙ ФАЙЛ. Правьте tools/make-module-templates.py и запускайте
  его заново - у модулей featured, bestseller, latest и special разметка
  общая, и руками эти четыре файла разойдутся при первой правке карточки.

  Модуль: __MODULE__.
  Движок отдаёт сюда products и heading_title. Название подборки задаётся
  в админке при добавлении модуля в макет страницы; если его не задали,
  заголовок не выводится - пустая строка вместо названия выглядела бы
  поломкой.
#}
{% if products %}
<section class="section">
  <div class="container">
    <div class="selection" data-slider>
      <div class="selection__head">
        <h2 class="section__title">{{ heading_title|default('') }}</h2>
        <div class="selection__nav">
          <button class="slider-btn" type="button" data-slider-prev aria-label="Предыдущие товары">__PREV__</button>
          <button class="slider-btn" type="button" data-slider-next aria-label="Следующие товары">__NEXT__</button>
        </div>
      </div>
      <div class="selection__line" data-slider-line tabindex="0" role="group" aria-label="{{ heading_title|default('Товары') }}">
{% for product in products %}
__CARD__{% endfor %}
      </div>
    </div>
  </div>
</section>
{% endif %}
"""


BEGIN = '{# КАРТОЧКА: начало'
END = '{# КАРТОЧКА: конец #}'

THEME_ROOT = pathlib.Path('opencart-theme/catalog/view/theme') / THEME / 'template'


def write_modules():
    OUT.mkdir(parents=True, exist_ok=True)
    for module in ('featured', 'bestseller', 'latest', 'special'):
        text = (BODY.replace('__MODULE__', module)
                    .replace('__PREV__', ICON_PREV)
                    .replace('__NEXT__', ICON_NEXT)
                    .replace('__CARD__', CARD))
        (OUT / f'{module}.twig').write_text(text, encoding='utf-8')
        print(f'  модуль {module}.twig')


def fill_markers():
    found = 0
    for path in sorted(THEME_ROOT.rglob('*.twig')):
        text = path.read_text(encoding='utf-8')
        if BEGIN not in text:
            continue
        if END not in text:
            print(f'  ОШИБКА {path}: есть метка начала, нет метки конца')
            return 1
        head = text[:text.index(BEGIN)]
        tail = text[text.index(END) + len(END):]
        marker = BEGIN + " — собирается tools/make-cards.py, руками не править #}\n"
        path.write_text(head + marker + CARD + END + tail, encoding='utf-8')
        print(f'  карточка -> {path.relative_to(THEME_ROOT)}')
        found += 1
    if not found:
        print('  меток в шаблонах не найдено')
    return 0


def main():
    write_modules()
    return fill_markers()


if __name__ == '__main__':
    sys.exit(main())
