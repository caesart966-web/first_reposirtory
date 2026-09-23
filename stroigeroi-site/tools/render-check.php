<?php
/*
  Проверка шаблонов темы НАСТОЯЩИМ Twig — тем же, на котором работает
  OpenCart. tools/twigcheck.py читает файлы глазами и ловит только то,
  что видно снаружи: незакрытый цикл, ссылку в никуда, чужой класс.
  Синтаксис он не разбирает, и выражение вроде
      {% set x = y matches '/^\d+$/' %}
  для него просто текст — а на сайте такая строка валит страницу целиком
  белым экраном.

  Здесь шаблон компилируется по-настоящему: если Twig его не понимает,
  проверка краснеет в CI, а не у заказчика.

  Вторая часть — разметка цены на карточке товара. Движок отдаёт цену
  готовой строкой («1 250,00 руб.»), а поисковику нужно число, и шаблон
  эту строку чистит. Правило чистки легко сломать незаметно: цифры
  в разметке разойдутся с ценой на странице, и об этом никто не узнает,
  потому что глазами разметку не видно. Поэтому страница товара
  собирается с десятком настоящих форматов цены и остатка, и результат
  сверяется с ожидаемым.

  Запуск:  php tools/render-check.php [папка-темы]
  Twig берётся из vendor/autoload.php (composer require twig/twig:^1.42)
  или из пути в переменной окружения TWIG_AUTOLOAD.
*/

$root  = $argv[1] ?? 'opencart-theme';
$theme = $root . '/catalog/view/theme/stroigeroi2026/template';

$autoload = getenv('TWIG_AUTOLOAD');
foreach ([$autoload, 'vendor/autoload.php', __DIR__ . '/../vendor/autoload.php'] as $cand) {
    if ($cand && is_file($cand)) { require $cand; $autoload = $cand; break; }
    $autoload = null;
}
if (!$autoload) {
    fwrite(STDERR, "Нет Twig. Поставьте: composer require twig/twig:^1.42\n");
    exit(2);
}
if (!is_dir($theme)) {
    fwrite(STDERR, "Нет папки шаблонов: $theme\n");
    exit(2);
}

$bad = 0;
$loader = new \Twig\Loader\FilesystemLoader($theme);
$twig   = new \Twig\Environment($loader, ['autoescape' => false, 'debug' => true]);

/* ---- 1. Каждый шаблон компилируется -------------------------------- */

$files = [];
$it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($theme));
foreach ($it as $f) {
    if ($f->isFile() && $f->getExtension() === 'twig') {
        $files[] = str_replace($theme . '/', '', $f->getPathname());
    }
}
sort($files);
foreach ($files as $name) {
    try {
        $twig->parse($twig->tokenize(new \Twig\Source(file_get_contents($theme . '/' . $name), $name)));
    } catch (\Twig\Error\Error $e) {
        echo "$name: строка {$e->getTemplateLine()}: {$e->getRawMessage()}\n";
        $bad++;
    }
}
echo 'Шаблонов скомпилировано: ' . count($files) . "\n";

/* ---- 2. Цена и наличие в разметке товара ---------------------------- */

$NB = "\u{00a0}";

// [цена, скидка, остаток, ожидаемое число или null, ожидаемое наличие или null]
$cases = [
    // Ровно так цена выглядит на живом stroigeroi.ru (снимок от 23.09.2026):
    // «руб» без точки. Самый важный случай в списке - это не придуманный
    // формат, а тот, что покупатели видят на самом деле.
    ['4 320,00 руб',         '',              '5',             '4320.00', 'InStock'],
    ['4' . $NB . '320,00 руб', '',            '5',             '4320.00', 'InStock'],
    ['1 250,00 руб.',        '',              '5',             '1250.00', 'InStock'],
    ['1' . $NB . '250,00 руб.', '',           '5',             '1250.00', 'InStock'],
    ['1 250.00 р.',          '',              '12',            '1250.00', 'InStock'],
    ['1 250 ₽',              '',              '3',             '1250',    'InStock'],
    ['1 250,00 руб.',        '999,00 руб.',   '2',             '999.00',  'InStock'],
    ['1 250,00 руб.',        '',              '0',             '1250.00', 'OutOfStock'],
    ['1 250,00 руб.',        '',              'В наличии',     '1250.00', 'InStock'],
    ['1 250,00 руб.',        '',              'Нет в наличии', '1250.00', 'OutOfStock'],
    ['1 250,00 руб.',        '',              'Под заказ',     '1250.00', null],
    ['$1,250.00',            '',              '5',             null,      null],  // другая валюта
    ['1.250,00 руб.',        '',              '5',             null,      null],  // другой формат
    ['',                     '',              '5',             null,      null],  // цены нет вовсе
];

$tpl = $twig->load('product/product.twig');

foreach ($cases as $i => [$price, $special, $stock, $want_price, $want_avail]) {
    $html = $tpl->render([
        'heading_title' => 'Плита OSB-3 9 мм',
        'price' => $price, 'special' => $special, 'stock' => $stock,
        'model' => 'OSB-9', 'manufacturer' => 'Kronospan', 'manufacturers' => 'index.php?route=x',
        'thumb' => 'image/a.jpg', 'product_id' => 7, 'breadcrumbs' => [
            ['text' => 'Главная', 'href' => 'index.php'],
            ['text' => 'Плиты',   'href' => 'index.php?route=y'],
        ],
    ]);

    $got_price = preg_match('~itemprop="price" content="([^"]*)"~', $html, $m) ? $m[1] : null;
    $got_avail = preg_match('~itemprop="availability" href="https://schema\.org/(\w+)"~', $html, $m) ? $m[1] : null;

    $label = sprintf('цена «%s»%s, остаток «%s»', $price, $special ? " скидка «{$special}»" : '', $stock);
    if ($got_price !== $want_price) {
        echo "product.twig: $label -> в разметке цена " . var_export($got_price, true)
           . ', ожидалось ' . var_export($want_price, true) . "\n";
        $bad++;
    }
    if ($got_avail !== $want_avail) {
        echo "product.twig: $label -> в разметке наличие " . var_export($got_avail, true)
           . ', ожидалось ' . var_export($want_avail, true) . "\n";
        $bad++;
    }
    // Цена в разметке обязана быть ценой со страницы, а не какой-то другой.
    if ($want_price !== null) {
        $shown = $special !== '' ? $special : $price;
        $digits = preg_replace('~\D~', '', $shown);
        if ($digits !== preg_replace('~\D~', '', $got_price ?? '')) {
            echo "product.twig: $label -> цифры разметки не совпали с ценой на странице\n";
            $bad++;
        }
    }
}
echo 'Форматов цены проверено: ' . count($cases) . "\n";

/* ---- 3. Крошки размечены для поисковика ----------------------------- */

$crumbs = $tpl->render([
    'heading_title' => 'Плита OSB-3 9 мм', 'price' => '1 250,00 руб.',
    'breadcrumbs' => [
        ['text' => 'Главная', 'href' => 'index.php'],
        ['text' => 'Плиты',   'href' => 'index.php?route=y'],
        ['text' => 'OSB',     'href' => 'index.php?route=z'],
    ],
]);
preg_match_all('~itemprop="position" content="(\d+)"~', $crumbs, $m);
if ($m[1] !== ['1', '2', '3']) {
    echo 'product.twig: номера крошек в разметке ' . json_encode($m[1]) . ", ожидались 1,2,3\n";
    $bad++;
}
// У последней крошки ссылки нет - это текущая страница.
if (substr_count($crumbs, 'itemprop="item"') !== 2) {
    echo 'product.twig: ссылок itemprop="item" в крошках ' . substr_count($crumbs, 'itemprop="item"')
       . ", ожидалось 2 (у последней крошки ссылки быть не должно)\n";
    $bad++;
}

/* ---- 4. Карточка магазина в шапке - разбираемый JSON ---------------- */

$head = $twig->load('common/header.twig')->render([
    'direction' => 'ltr', 'lang' => 'ru', 'title' => 'Строй-Герой',
    'base' => 'https://stroigeroi.ru/', 'categories' => [], 'styles' => [], 'scripts' => [], 'links' => [],
]);
preg_match_all('~<script type="application/ld\+json">(.*?)</script>~s', $head, $m);
if (!$m[1]) {
    echo "header.twig: карточки магазина для поисковика (ld+json) нет вовсе\n";
    $bad++;
}
foreach ($m[1] as $i => $json) {
    $d = json_decode($json, true);
    if ($d === null) {
        echo 'header.twig: разметка ld+json #' . ($i + 1) . ' не разбирается: ' . json_last_error_msg() . "\n";
        $bad++;
        continue;
    }
    foreach (['@context', '@type', 'name', 'telephone'] as $key) {
        if (empty($d[$key])) { echo "header.twig: в разметке ld+json пусто поле $key\n"; $bad++; }
    }
    if (empty($d['department'])) {
        echo "header.twig: в разметке магазина нет ни одной точки (department)\n";
        $bad++;
    }
    // Телефон и адреса в разметке обязаны стоять и на самой странице,
    // иначе поисковик покажет одно, а посетитель увидит другое.
    // Саму разметку из поиска вычёркиваем: иначе адрес находится
    // в ней же, и проверка всегда довольна собой.
    $page = preg_replace('~<script type="application/ld\+json">.*?</script>~s', '', $head);
    foreach ($d['department'] ?? [] as $dep) {
        $street = $dep['address']['streetAddress'] ?? '';
        if ($street && strpos($page, $street) === false) {
            echo "header.twig: адрес «{$street}» есть в разметке, но не на странице\n";
            $bad++;
        }
    }
}
echo 'Разметок ld+json в шапке: ' . count($m[1]) . "\n";

/* ---- 5. Раздел-отдел: товаров нет, подразделы есть ------------------- */
/* «Инструменты» после выгрузки из 1С держат товары уровнем ниже.
   Написать на такой странице «пока пусто» - значит отправить человека
   прочь от девяти полных подразделов: на телефоне боковая колонка
   с ними свёрнута, и «пусто» - единственное, что он увидит. */

$cat = $twig->load('product/category.twig');
$EMPTY = 'В этом разделе пока пусто';
$subs = [
    ['name' => 'Дрели, шуруповёрты, перфораторы', 'href' => 'index.php?route=product/category&path=59_90'],
    ['name' => 'Пилы, цепи и шины',               'href' => 'index.php?route=product/category&path=59_91'],
];

$dept = $cat->render(['heading_title' => 'Инструменты', 'products' => [], 'categories' => $subs]);
if (strpos($dept, $EMPTY) !== false) {
    echo "category.twig: раздел с подразделами и без своих товаров пишет «{$EMPTY}»\n";
    $bad++;
}
foreach ($subs as $sub) {
    $href = htmlspecialchars($sub['href'], ENT_QUOTES);
    if (substr_count($dept, 'class="category-card" href="' . $sub['href'] . '"') + substr_count($dept, 'class="category-card" href="' . $href . '"') < 1) {
        echo "category.twig: нет плитки подраздела «{$sub['name']}» по центру страницы\n";
        $bad++;
    }
}

$none = $cat->render(['heading_title' => 'Сантехника', 'products' => [], 'categories' => []]);
if (strpos($none, $EMPTY) === false) {
    echo "category.twig: совсем пустой раздел не говорит «{$EMPTY}» и не даёт телефон\n";
    $bad++;
}

$full = $cat->render(['heading_title' => 'Дрели', 'categories' => [], 'products' => [[
    'product_id' => 1, 'thumb' => 'image/a.jpg', 'name' => 'Дрель', 'href' => '#',
    'price' => '4 320,00 руб', 'special' => '', 'description' => '', 'rating' => 0,
]]]);
if (strpos($full, $EMPTY) !== false || strpos($full, 'class="category-card"') !== false) {
    echo "category.twig: раздел с товарами показывает «пусто» или плитки подразделов вместо товаров\n";
    $bad++;
}
echo "Страница раздела: 3 состояния проверено\n";

/*
 * Значки отделов в меню каталога. Подбираются по куску названия, и правка
 * одного слова в menu.twig молча вернула бы отделу общую коробку - глазами
 * это замечают, только открыв меню. Названия - 15 отделов живой базы
 * на 23.09.2026, значки - те, что стоят у этих отделов в макете.
 */
$want = [
    'Инструменты' => 'toolbox', 'Электрика и свет' => 'bulb',
    'Сантехника и инженерные системы' => 'pipe', 'Ручной инструмент' => 'wrench',
    'Автотовары' => 'car', 'Всё для сада' => 'sprout', 'Крепёж и фурнитура' => 'nut',
    'Отделочные и стройматериалы' => 'bricks', 'Офис и дом' => 'house',
    'Спорт и туризм' => 'backpack', 'Станки и промкомпоненты' => 'gear',
    'Климат, отопление и вентиляция' => 'radiator', 'Клининг и химия' => 'spray',
    'Строительное оборудование' => 'crane', 'Расходка, спецодежда и сиз' => 'helmet',
    'Раздел, которого нет в списке' => 'box',
];
$menuSrc = file_get_contents("$theme/common/menu.twig");
preg_match_all("~'(\\w+)': '([^']*)'~", $menuSrc, $pairs, PREG_SET_ORDER);
$iconOf = [];
foreach ($pairs as $pair) $iconOf[$pair[2]] = $pair[1];
$cats = [];
foreach (array_keys($want) as $i => $name) {
    $cats[] = ['name' => $name, 'href' => "https://stroigeroi.ru/r$i", 'children' => [], 'column' => 1];
}
$menu = $twig->load('common/menu.twig')->render(['categories' => $cats]);
preg_match('~<div class="catalog-menu__grid">(.*?)</div>~s', $menu, $grid);
preg_match_all('~<a class="catalog-menu__link" href="[^"]*"><svg[^>]*>(.*?)</svg><span>([^<]*)</span></a>~s',
    $grid ? $grid[1] : '', $links, PREG_SET_ORDER);
$got = [];
foreach ($links as $link) $got[$link[2]] = $iconOf[$link[1]] ?? 'неизвестный';
foreach ($want as $name => $icon) {
    $has = $got[$name] ?? 'нет в меню';
    if ($has !== $icon) {
        echo "menu.twig: у отдела «{$name}» значок {$has}, а в макете {$icon}\n";
        $bad++;
    }
}
if ($grid && trim(preg_replace('~<a .*?</a>~s', '', $grid[1])) !== '') {
    echo "menu.twig: между ссылками меню остался текст — след опечатки в логике значков\n";
    $bad++;
}
echo 'Значки отделов: ' . count($want) . " названий проверено\n";

exit($bad ? 1 : 0);
