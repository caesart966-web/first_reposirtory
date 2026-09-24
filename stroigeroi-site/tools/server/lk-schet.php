<?php
/*
  Сколько на сайте пользуются личным кабинетом. Вопрос заказчика
  24.09.2026: «а нам кабинет вообще нужен?» - ответ по цифрам, а не
  на глаз. Только читает базу и печатает числа и даты: ни имён, ни почт,
  ни телефонов - вывод присылают снимком. Через сайт не работает.

  «Заказ» здесь - заказ с любым статусом, кроме нулевого: с нулевым движок
  хранит брошенные на оформлении, они посчитаны отдельно. «Из кабинета» -
  у заказа есть номер покупателя: вошёл в кабинет или завёл его, оформляя
  заказ. «Гостем» - без кабинета.

  Запуск: php lk-schet.php <папка сайта>
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

// Одна строка результата или null, если запрос не прошёл (нет таблицы).
$row = function ($sql) use ($m) {
    $r = $m->query($sql);
    return $r ? $r->fetch_row() : null;
};
$rows = function ($sql) use ($m) {
    $r = $m->query($sql);
    $out = array();
    while ($r && ($x = $r->fetch_row())) {
        $out[] = $x;
    }
    return $out;
};
$d = function ($s) {
    return $s ? date('d.m.Y', strtotime($s)) : '-';
};
$year = "date_added >= NOW() - INTERVAL 12 MONTH";

echo "-- customers\n";
$c = $row("SELECT COUNT(*), MIN(date_added), MAX(date_added), SUM(status = 0), SUM(newsletter = 1) FROM `{$p}customer`");
if (!$c) {
    echo "таблицы покупателей нет - считать нечего\n";
    exit(1);
}
echo 'кабинетов всего: ', $c[0], ' (первый заведён ', $d($c[1]), ', последний ', $d($c[2]), ")\n";
$by = array();
foreach ($rows("SELECT YEAR(date_added), COUNT(*) FROM `{$p}customer` GROUP BY 1 ORDER BY 1") as $x) {
    $by[] = "{$x[0]} - {$x[1]}";
}
echo 'заведено по годам: ', $by ? implode(', ', $by) : '-', "\n";
$bots = $row("SELECT COUNT(*) FROM `{$p}customer` WHERE CONCAT(firstname, ' ', lastname, ' ', email) LIKE '%http%'"
    . " OR CONCAT(firstname, ' ', lastname) LIKE '%www.%' OR CONCAT(firstname, ' ', lastname) LIKE '%.ru%'"
    . " OR CONCAT(firstname, ' ', lastname) LIKE '%.com%'");
echo 'со ссылкой в имени (так заводят кабинет роботы-рассыльщики): ', $bots ? $bots[0] : '-', "\n";
$buyers = $row("SELECT COUNT(DISTINCT customer_id) FROM `{$p}order` WHERE customer_id > 0 AND order_status_id > 0");
echo 'из них хоть раз что-то заказали: ', $buyers ? $buyers[0] : '-', ' из ', $c[0], "\n";
echo "отключены в админке: " . (int)$c[3] . ", подписаны на рассылку: " . (int)$c[4] . "\n";
$act = $row("SELECT COUNT(*), SUM(`key` = 'login' AND $year), COUNT(DISTINCT IF(`key` = 'login' AND $year, customer_id, NULL)) FROM `{$p}customer_activity`");
if ($act && $act[0] > 0) {
    echo "входили в кабинет за 12 месяцев - покупателей: " . (int)$act[2] . ", входов: " . (int)$act[1] . "\n";
} else {
    echo "журнал входов в админке выключен - сколько раз входили, не узнать\n";
}
$ip = $row("SELECT COUNT(DISTINCT customer_id) FROM `{$p}customer_ip` WHERE $year");
if ($ip) {
    echo "входили с нового для себя адреса за 12 месяцев - покупателей: {$ip[0]} (это нижняя граница: вход с прежнего адреса не записывается)\n";
}

echo "-- orders\n";
$o = $row("SELECT COUNT(*), MIN(date_added), MAX(date_added), SUM(customer_id > 0), SUM(customer_id = 0) FROM `{$p}order` WHERE order_status_id > 0");
if (!$o || !$o[0]) {
    echo "заказов с сайта нет\n";
} else {
    echo 'заказов всего: ', $o[0], ' (с ', $d($o[1]), ' по ', $d($o[2]), '), из кабинета: ', (int)$o[3], ', гостем: ', (int)$o[4], "\n";
    $o12 = $row("SELECT COUNT(*), SUM(customer_id > 0), SUM(customer_id = 0), COUNT(DISTINCT IF(customer_id > 0, customer_id, NULL)) FROM `{$p}order` WHERE order_status_id > 0 AND $year");
    echo "за 12 месяцев: " . (int)$o12[0] . ", из кабинета: " . (int)$o12[1] . " (разных покупателей " . (int)$o12[3] . "), гостем: " . (int)$o12[2] . "\n";
    $by = array();
    foreach ($rows("SELECT YEAR(date_added), COUNT(*), SUM(customer_id > 0) FROM `{$p}order` WHERE order_status_id > 0 GROUP BY 1 ORDER BY 1") as $x) {
        $by[] = "{$x[0]} - {$x[1]} (из кабинета {$x[2]})";
    }
    echo 'по годам: ', implode(', ', $by), "\n";
    $last = $row("SELECT MAX(date_added) FROM `{$p}order` WHERE order_status_id > 0 AND customer_id > 0");
    echo 'последний заказ из кабинета: ', $d($last ? $last[0] : null), "\n";
    $st = array();
    foreach ($rows("SELECT IFNULL(s.name, o.order_status_id), COUNT(*) FROM `{$p}order` o LEFT JOIN `{$p}order_status` s"
        . " ON s.order_status_id = o.order_status_id AND s.language_id = o.language_id"
        . " WHERE o.order_status_id > 0 AND o.$year GROUP BY o.order_status_id ORDER BY 2 DESC") as $x) {
        $st[] = "{$x[0]} - {$x[1]}";
    }
    echo 'статусы за 12 месяцев: ', $st ? implode(', ', $st) : '-', "\n";
}
$ab = $row("SELECT COUNT(*), SUM($year) FROM `{$p}order` WHERE order_status_id = 0");
if ($ab) {
    echo "брошены на оформлении: " . (int)$ab[0] . ", из них за 12 месяцев: " . (int)$ab[1] . "\n";
}

echo "-- other\n";
$w = $row("SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM `{$p}customer_wishlist`");
echo 'избранное в кабинетах: ', $w ? "товаров {$w[0]}, покупателей {$w[1]}" : '-', "\n";
$r = $row("SELECT COUNT(*), SUM($year) FROM `{$p}return`");
echo 'заявок на возврат через сайт: ', $r ? (int)$r[0] . ', из них за 12 месяцев: ' . (int)$r[1] : '-', "\n";
