<?php
/*
  Как радиаторы записаны в каталоге магазина. Нужно для следующего шага
  калькулятора (просьба заказчика 26.09.2026): «человек вводит свои
  характеристики, и сайт предлагает все виды радиаторов исходя из количества
  секций, которыми мы торгуем». Для этого калькулятор должен знать мощность
  секции каждой модели, а где она записана - в характеристиках, в опциях
  или только в названии, - из среды разработки не видно.

  Только читает базу и печатает названия разделов, характеристик и опций,
  примеры названий товаров, цены и остатки. Покупателей не касается.

  Запуск: php radiatory.php <папка сайта>
*/
if (PHP_SAPI !== 'cli') {
    exit;
}
$site = isset($argv[1]) ? rtrim($argv[1], '/') : '.';
require $site . '/config.php';
mysqli_report(MYSQLI_REPORT_OFF);
$m = @new mysqli(DB_HOSTNAME, DB_USERNAME, DB_PASSWORD, DB_DATABASE, (int)DB_PORT);
if ($m->connect_error) {
    echo 'DB: ', $m->connect_error, "\n";
    exit(1);
}
$m->set_charset('utf8');
$p = DB_PREFIX;
echo "-- radiatory\n";

$rows = function ($sql) use ($m) {
    $r = $m->query($sql);
    $out = array();
    while ($r && ($x = $r->fetch_row())) {
        $out[] = $x;
    }
    return $out;
};
// Текст из базы хранится экранированным (&quot;) - печатаем как на сайте.
$t = function ($s, $len) {
    $s = trim(preg_replace('/\s+/u', ' ', html_entity_decode((string)$s, ENT_QUOTES, 'UTF-8')));
    return mb_strlen($s) > $len ? mb_substr($s, 0, $len - 1) . '…' : $s;
};

$lang = $rows("SELECT l.language_id FROM `{$p}language` l JOIN `{$p}setting` s ON s.`value` = l.code"
    . " WHERE s.store_id = 0 AND s.`key` = 'config_language'");
$L = $lang ? (int)$lang[0][0] : 0;
if ($L <= 0) {
    $lang = $rows("SELECT MIN(language_id) FROM `{$p}language`");
    $L = $lang ? (int)$lang[0][0] : 1;
}

// Разделы со словом «радиатор» в названии.
$cats = $rows("SELECT c.category_id, cd.name, c.status FROM `{$p}category` c JOIN `{$p}category_description` cd"
    . " ON cd.category_id = c.category_id AND cd.language_id = $L WHERE cd.name LIKE '%адиатор%' ORDER BY cd.name");
$ids = array();
foreach ($cats as $c) {
    $ids[] = (int)$c[0];
}
echo 'разделов со словом «радиатор»: ', count($cats), "\n";
foreach ($cats as $c) {
    $n = $rows("SELECT COUNT(*), SUM(p.status = 1) FROM `{$p}product_to_category` pc JOIN `{$p}product` p"
        . " ON p.product_id = pc.product_id WHERE pc.category_id = " . (int)$c[0]);
    echo '  «', $t($c[1], 60), '» id ', $c[0], $c[2] ? '' : ' (выключен)', ', товаров ', (int)$n[0][0],
         ' (включено ', (int)$n[0][1], ")\n";
}

// Радиаторы: товары этих разделов и все, у кого «радиатор» в названии.
$where = "pd.name LIKE '%адиатор%'";
if ($ids) {
    $where .= " OR p.product_id IN (SELECT product_id FROM `{$p}product_to_category` WHERE category_id IN (" . implode(',', $ids) . "))";
}
$prod = $rows("SELECT p.product_id FROM `{$p}product` p JOIN `{$p}product_description` pd"
    . " ON pd.product_id = p.product_id AND pd.language_id = $L WHERE $where");
$pids = array();
foreach ($prod as $x) {
    $pids[] = (int)$x[0];
}
if (!$pids) {
    echo "товаров-радиаторов не нашлось: ни в разделах выше, ни по названию\n";
    exit;
}
$in = implode(',', $pids);
$s = $rows("SELECT COUNT(*), SUM(status = 1), SUM(status = 1 AND price > 0), SUM(status = 1 AND quantity > 0) FROM `{$p}product` WHERE product_id IN ($in)");
echo 'товаров-радиаторов: ', (int)$s[0][0], ', включено ', (int)$s[0][1], ', из них с ценой ', (int)$s[0][2],
     ', в наличии ', (int)$s[0][3], "\n";
$named = $rows("SELECT SUM(pd.name LIKE '%секц%'), SUM(pd.name LIKE '%Вт%' OR pd.name LIKE '%кВт%') FROM `{$p}product_description` pd"
    . " WHERE pd.language_id = $L AND pd.product_id IN ($in)");
echo 'в названии есть «секц…»: ', (int)$named[0][0], ', «Вт»: ', (int)$named[0][1], "\n";

// Характеристики (атрибуты) - где может стоять мощность секции.
$attrs = $rows("SELECT pa.attribute_id, ad.name, COUNT(DISTINCT pa.product_id) FROM `{$p}product_attribute` pa"
    . " JOIN `{$p}attribute_description` ad ON ad.attribute_id = pa.attribute_id AND ad.language_id = $L"
    . " WHERE pa.language_id = $L AND pa.product_id IN ($in) GROUP BY pa.attribute_id, ad.name ORDER BY 3 DESC LIMIT 15");
echo 'характеристики: ', $attrs ? count($attrs) : 'нет', "\n";
foreach ($attrs as $a) {
    $vals = $rows("SELECT DISTINCT `text` FROM `{$p}product_attribute` WHERE attribute_id = " . (int)$a[0]
        . " AND language_id = $L AND product_id IN ($in) LIMIT 3");
    $v = array();
    foreach ($vals as $x) {
        $v[] = '«' . $t($x[0], 30) . '»';
    }
    echo '  «', $t($a[1], 40), '» - у ', $a[2], ', например ', implode(', ', $v), "\n";
}

// Опции - так бывает записано число секций с доплатой.
$opts = $rows("SELECT po.option_id, od.name, COUNT(DISTINCT po.product_id) FROM `{$p}product_option` po"
    . " JOIN `{$p}option_description` od ON od.option_id = po.option_id AND od.language_id = $L"
    . " WHERE po.product_id IN ($in) GROUP BY po.option_id, od.name ORDER BY 3 DESC LIMIT 10");
echo 'опции: ', $opts ? count($opts) : 'нет', "\n";
foreach ($opts as $o) {
    $vals = $rows("SELECT DISTINCT ovd.name FROM `{$p}product_option_value` pov JOIN `{$p}option_value_description` ovd"
        . " ON ovd.option_value_id = pov.option_value_id AND ovd.language_id = $L"
        . " WHERE pov.option_id = " . (int)$o[0] . " AND pov.product_id IN ($in) LIMIT 8");
    $v = array();
    foreach ($vals as $x) {
        $v[] = $t($x[0], 20);
    }
    echo '  «', $t($o[1], 40), '» - у ', $o[2], ': ', implode(', ', $v), "\n";
}

// Примеры - по названию видно, пишут ли в нём секции и мощность.
$ex = $rows("SELECT p.product_id, pd.name, p.model, p.price, p.quantity FROM `{$p}product` p JOIN `{$p}product_description` pd"
    . " ON pd.product_id = p.product_id AND pd.language_id = $L WHERE p.product_id IN ($in) AND p.status = 1 ORDER BY pd.name LIMIT 8");
echo "примеры:\n";
foreach ($ex as $x) {
    echo '  ', $x[0], ' «', $t($x[1], 70), '», модель ', $t($x[2], 20), ', ', number_format((float)$x[3], 0, ',', ' '),
         ' руб, остаток ', (int)$x[4], "\n";
}
