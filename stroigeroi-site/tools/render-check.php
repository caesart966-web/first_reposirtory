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
    $plain = strip_tags($head);
    foreach ($d['department'] ?? [] as $dep) {
        $street = $dep['address']['streetAddress'] ?? '';
        if ($street && strpos($head, $street) === false) {
            echo "header.twig: адрес «$street» есть в разметке, но не на странице\n";
            $bad++;
        }
    }
}
echo 'Разметок ld+json в шапке: ' . count($m[1]) . "\n";

exit($bad ? 1 : 0);
