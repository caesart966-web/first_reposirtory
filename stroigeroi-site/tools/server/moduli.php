<?php
/*
  Серверная часть правки 36: что стоит на главной в админке. Только
  читает базу; запускается из командной строки (команда в сообщении
  заказчику) и сразу удаляется; через сайт не работает.

  «Популярные товары» на главной - это модули движка в позиции Content
  Top макета главной: «Рекомендуем» (товары выбирают руками), «Лидеры
  продаж», «Новинки», «Акции». Заголовки вкладок - их названия из
  языковых файлов ocStore. Скрипт печатает, какие модули стоят в макете,
  включены ли они и сколько товаров выбрано, и четыре цифры каталога,
  от которых зависит, будет ли подборке что показать:
    фото    - у скольких товаров в продаже есть картинка и файл на диске;
    скидки  - у скольких действует скидка сейчас (вкладка «Акции»);
    дни     - за сколько разных дней товары попали в каталог: «Новинки»
              показывают последние по дате, а после разового импорта
              из 1С дата у всех одна, и «новинки» выходят случайные;
    заказы  - сколько заказов в магазине (по ним считает «Лидеры продаж»).
  Ни покупателей, ни телефонов, ни сумм не печатает.

  Запуск: php moduli.php <папка сайта>
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
$one = function ($sql) use ($m) {
    $r = $m->query($sql);
    $row = $r ? $r->fetch_row() : null;
    return $row ? $row[0] : null;
};
echo "-- moduli\n";

$PRODUCT = array('featured', 'bestseller', 'latest', 'special');
$installed = array();
$r = $m->query("SELECT code FROM `{$p}extension` WHERE type = 'module'");
while ($r && ($row = $r->fetch_row())) {
    $installed[] = $row[0];
}
echo 'установлены: ', implode(', ', array_intersect($PRODUCT, $installed)) ?: 'ни одного модуля товаров', "\n";

// Описание модуля с настройками (featured.28 и т. п.): название в админке,
// включён ли, сколько показывать, а у «Рекомендуем» - сколько товаров
// выбрано и сколько из них в продаже.
$describe = function ($code) use ($m, $p, $one) {
    if (!preg_match('/^(\w+)\.(\d+)$/', $code, $mm)) {
        $on = $one("SELECT value FROM `{$p}setting` WHERE store_id = 0 AND `key` = 'module_"
            . $m->real_escape_string($code) . "_status'");
        return $on ? 'вкл' : 'ВЫКЛ';
    }
    $r = $m->query("SELECT name, setting FROM `{$p}module` WHERE module_id = " . (int)$mm[2]);
    $mod = $r ? $r->fetch_assoc() : null;
    if (!$mod) {
        return 'модуля нет в базе';
    }
    $set = json_decode($mod['setting'], true);
    if (!is_array($set)) {
        $set = array();
    }
    $out = '«' . $mod['name'] . '» ' . (!empty($set['status']) ? 'вкл' : 'ВЫКЛ');
    if (isset($set['limit'])) {
        $out .= ', показывать ' . (int)$set['limit'];
    }
    if ($mm[1] === 'featured') {
        $ids = isset($set['product']) && is_array($set['product']) ? array_map('intval', $set['product']) : array();
        $alive = $ids ? (int)$one("SELECT COUNT(*) FROM `{$p}product` WHERE status = 1 AND product_id IN ("
            . implode(',', $ids) . ')') : 0;
        $out .= ', выбрано товаров ' . count($ids) . ' (в продаже ' . $alive . ')';
    }
    return $out;
};

$home = 0;
$r = $m->query("SELECT l.layout_id, l.name FROM `{$p}layout_route` lr JOIN `{$p}layout` l ON l.layout_id = lr.layout_id"
    . " WHERE lr.route = 'common/home' AND lr.store_id = 0");
$row = $r ? $r->fetch_assoc() : null;
if (!$row) {
    echo "макет главной (common/home) не найден\n";
} else {
    $home = (int)$row['layout_id'];
    echo 'макет главной: «', $row['name'], '» (', $home, ')', "\n";
    $r = $m->query("SELECT code, position, sort_order FROM `{$p}layout_module` WHERE layout_id = $home"
        . ' ORDER BY position, sort_order');
    if (!$r || !$r->num_rows) {
        echo "  модулей в макете нет\n";
    }
    while ($r && ($lm = $r->fetch_assoc())) {
        echo '  ', $lm['position'], ' ', (int)$lm['sort_order'], ': ', $lm['code'], ' ', $describe($lm['code']), "\n";
    }
}

// Модули товаров, заведённые, но не стоящие на главной: их можно
// просто поставить в макет, не заводя заново.
$r = $m->query("SELECT module_id, code FROM `{$p}module` WHERE code IN ('" . implode("','", $PRODUCT) . "') ORDER BY module_id");
$spare = array();
while ($r && ($mod = $r->fetch_assoc())) {
    $code = $mod['code'] . '.' . $mod['module_id'];
    $on = $home ? $one("SELECT COUNT(*) FROM `{$p}layout_module` WHERE layout_id = $home AND code = '"
        . $m->real_escape_string($code) . "'") : 0;
    if (!$on) {
        $spare[] = $code . ' ' . $describe($code);
    }
}
echo 'заведены, но не на главной: ', $spare ? implode('; ', $spare) : 'нет', "\n";

// Цифры каталога
$group = (int)$one("SELECT value FROM `{$p}setting` WHERE store_id = 0 AND `key` = 'config_customer_group_id'");
$total = 0;
$photo = 0;
$r = $m->query("SELECT image FROM `{$p}product` WHERE status = 1");
while ($r && ($row = $r->fetch_row())) {
    $total++;
    if ($row[0] !== null && $row[0] !== '' && is_file($site . '/image/' . $row[0])) {
        $photo++;
    }
}
$sale = (int)$one("SELECT COUNT(DISTINCT ps.product_id) FROM `{$p}product_special` ps"
    . " JOIN `{$p}product` pr ON pr.product_id = ps.product_id"
    . " WHERE pr.status = 1 AND ps.customer_group_id = $group"
    . " AND (ps.date_start = '0000-00-00' OR ps.date_start < NOW())"
    . " AND (ps.date_end = '0000-00-00' OR ps.date_end > NOW())");
$days = (int)$one("SELECT COUNT(DISTINCT DATE(date_added)) FROM `{$p}product` WHERE status = 1");
$last = $one("SELECT DATE(MAX(date_added)) FROM `{$p}product` WHERE status = 1");
$orders = (int)$one("SELECT COUNT(*) FROM `{$p}order` WHERE order_status_id > 0");
echo "каталог: в продаже $total, с фото $photo, со скидкой сейчас $sale, дней поступления $days",
     $last ? " (последний $last)" : '', ", заказов $orders\n";
