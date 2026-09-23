<?php
/*
 * Страницы темы с самыми неудобными названиями из выгрузки 1С - для
 * tools/test-long-names.mjs, который смотрит их в браузере.
 *
 * В 1С характеристики пишут через запятую без пробелов, и в названии
 * товара бывает кусок в 37 знаков без единого места для переноса:
 * «HTR0001,140x80x38мм,-32+350С,точность». Раздел мог прийти одним
 * словом капсом - «ЭЛЕКТРОИНСТРУМЕНТЫ». Глазами такое находят только
 * с телефона: заказчик нашёл слово, вылезшее из плитки.
 *
 * Берутся восемь товаров с самыми длинными кусками без пробелов из
 * 1c/import.sql (то есть ровно то, что уехало на сайт) и собираются:
 * раздел с товарами, раздел с плитками подразделов, карточка товара,
 * корзина и сравнение. Шаблоны - настоящим Twig, как в render-check.php.
 *
 * Запуск: TWIG_AUTOLOAD=.../autoload.php php tools/render-long-names.php <папка>
 */

$root = dirname(__DIR__);
$theme = $root . '/opencart-theme/catalog/view/theme/stroigeroi2026';
$out = $argv[1] ?? sys_get_temp_dir() . '/long-names';
@mkdir($out, 0777, true);

$autoload = getenv('TWIG_AUTOLOAD');
foreach ([$autoload, $root . '/vendor/autoload.php'] as $cand) {
    if ($cand && is_file($cand)) { require $cand; $autoload = $cand; break; }
    $autoload = null;
}
if (!$autoload) { fwrite(STDERR, "Нет Twig: укажите TWIG_AUTOLOAD\n"); exit(2); }

// Названия товаров из собранного SQL: строки вида ('guid', 'guid', 'название', ...
preg_match_all("~^\s*\('[0-9a-f-]{36}', '[0-9a-f-]{36}', '((?:[^'\\\\]|\\\\.|'')*)'~mu",
    file_get_contents($root . '/1c/import.sql'), $m);
$names = array_map(function ($n) { return str_replace(["\\'", "''", '\\\\'], ["'", "'", '\\'], $n); }, $m[1]);
if (count($names) < 8) { fwrite(STDERR, "В 1c/import.sql не нашлось названий товаров\n"); exit(2); }
$longest = function ($n) { return max(array_map('mb_strlen', preg_split('/\s+/u', $n))); };
usort($names, function ($a, $b) use ($longest) { return $longest($b) - $longest($a); });
$long = array_slice($names, 0, 8);

$twig = new \Twig\Environment(new \Twig\Loader\FilesystemLoader("$theme/template"), ['autoescape' => false]);
$wrap = function ($html) use ($theme) {
    return "<!doctype html><html lang=\"ru\" data-theme=\"light\"><head><meta charset=\"utf-8\">"
        . "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        . "<link rel=\"stylesheet\" href=\"file://$theme/stylesheet/style.css\">"
        . "<link rel=\"stylesheet\" href=\"file://$theme/stylesheet/opencart.css\"></head>"
        . "<body><main>$html</main></body></html>";
};
$crumbs = [['text' => 'Главная', 'href' => '#'], ['text' => 'Строительное оборудование', 'href' => '#'], ['text' => $long[0], 'href' => '#']];
$common = ['header' => '', 'footer' => '', 'content_top' => '', 'content_bottom' => '', 'column_left' => '',
           'breadcrumbs' => $crumbs, 'continue' => '#'];
$price = '12 345,00&nbsp;руб';

$cards = [];
foreach ($long as $i => $n) {
    $cards[] = ['product_id' => $i + 1, 'thumb' => '', 'name' => $n, 'href' => '#', 'price' => $price,
                'special' => $i == 1 ? '9 999,00&nbsp;руб' : '', 'description' => '', 'rating' => 0];
}
$pages = [];
$pages['category'] = $twig->load('product/category.twig')->render($common + [
    'heading_title' => 'Строительное оборудование', 'products' => $cards, 'categories' => [],
    'sorts' => [], 'limits' => [], 'pagination' => '', 'results' => '']);
$subs = [];
foreach (['ЭЛЕКТРОИНСТРУМЕНТЫ', 'Лобзики, рубанки, ручной инструмент', 'Аккумуляторы, зарядные, патроны',
          'Краскопульты и пневмоинструмент', 'Климат, отопление и вентиляция'] as $n) {
    $subs[] = ['name' => $n, 'href' => '#'];
}
$pages['department'] = $twig->load('product/category.twig')->render($common + [
    'heading_title' => 'ЭЛЕКТРОИНСТРУМЕНТЫ', 'products' => [], 'categories' => $subs]);
$pages['product'] = $twig->load('product/product.twig')->render($common + [
    'heading_title' => $long[0], 'thumb' => '', 'popup' => '', 'images' => [], 'price' => $price, 'special' => '',
    'stock' => '5', 'model' => 'HTR0001', 'product_id' => 1, 'minimum' => 1, 'options' => [],
    'attribute_groups' => [], 'description' => '', 'products' => array_slice($cards, 0, 4),
    'manufacturer' => '', 'review_status' => 0, 'tags' => []]);
$rows = [];
foreach (array_slice($long, 0, 4) as $i => $n) {
    $rows[] = ['cart_id' => $i, 'thumb' => '', 'name' => $n, 'href' => '#', 'model' => 'HTR0001', 'option' => [],
               'quantity' => 2, 'stock' => $i != 2, 'price' => $price, 'total' => '24 690,00&nbsp;руб',
               'reward' => '', 'recurring' => ''];
}
$pages['cart'] = $twig->load('checkout/cart.twig')->render($common + [
    'products' => $rows, 'vouchers' => [], 'totals' => [['title' => 'Итого', 'text' => '98 760,00&nbsp;руб']],
    'action' => '#', 'checkout' => '#', 'modules' => [], 'error_warning' => '', 'success' => '', 'attention' => '']);
$cmp = [];
foreach (array_slice($long, 0, 3) as $i => $n) {
    $cmp[$i + 1] = ['product_id' => $i + 1, 'name' => $n, 'thumb' => '', 'price' => $price, 'special' => '',
                    'description' => '', 'model' => 'HTR0001', 'manufacturer' => 'Hammer', 'availability' => 'В наличии',
                    'minimum' => 1, 'rating' => 0, 'reviews' => '', 'weight' => '', 'length' => '', 'width' => '',
                    'height' => '', 'attribute' => [], 'href' => '#', 'remove' => '#'];
}
$pages['compare'] = $twig->load('product/compare.twig')->render($common + [
    'products' => $cmp, 'attribute_groups' => [], 'review_status' => 0]);

foreach ($pages as $name => $html) file_put_contents("$out/$name.html", $wrap($html));
echo 'Собрано страниц: ' . count($pages) . ', самый длинный кусок без пробела: '
    . $longest($long[0]) . " знаков («{$long[0]}»)\n";
