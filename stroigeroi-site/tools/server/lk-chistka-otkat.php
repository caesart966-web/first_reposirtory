<?php
/*
  Откат lk-chistka.php: возвращает удалённые кабинеты и всё, что удалено
  вместе с ними, из таблиц lk_bak_*. Только из командной строки.

  Кабинет не возвращается, если его номер успел занять другой, новый
  кабинет: иначе к новому покупателю приписались бы чужие адреса и входы.
  Свой кабинет узнаётся по почте и дате заведения. Строки, которые
  остались на месте (чистка оборвалась на середине), пропускаются.

  Вернулось всё - копии удаляются. Не вернулось хоть что-то - копии
  остаются, а в отчёте сказано сколько.

  Запуск: php lk-chistka-otkat.php <папка сайта>
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
$m->query("SET SESSION sql_mode = 'NO_ZERO_IN_DATE,NO_ENGINE_SUBSTITUTION'");
$p = DB_PREFIX;

$exists = function ($t) use ($m, $p) {
    $r = $m->query("SHOW TABLES LIKE '" . $m->real_escape_string($p . $t) . "'");
    return $r && $r->num_rows > 0;
};
$count = function ($sql) use ($m) {
    $r = $m->query($sql);
    return $r ? (int)$r->fetch_row()[0] : -1;
};
$TABLES = array('customer', 'address', 'cart', 'customer_activity', 'customer_approval', 'customer_ip',
                'customer_online', 'customer_search', 'customer_wishlist');

if (!$exists('lk_bak_customer')) {
    echo "нет таблицы {$p}lk_bak_customer - откатывать нечего\n";
    exit;
}
// Чьи строки возвращать: кабинета нет или на месте тот же самый.
$m->query("DROP TABLE IF EXISTS `{$p}lk_vernut`");
if (!$m->query("CREATE TABLE `{$p}lk_vernut` (customer_id INT NOT NULL PRIMARY KEY)")
    || !$m->query("INSERT INTO `{$p}lk_vernut` SELECT b.customer_id FROM `{$p}lk_bak_customer` b"
        . " LEFT JOIN `{$p}customer` c ON c.customer_id = b.customer_id"
        . " WHERE c.customer_id IS NULL OR (c.email = b.email AND c.date_added = b.date_added)")) {
    echo 'STOP: ', $m->error, " - ничего не менял\n";
    exit(1);
}
$taken = $count("SELECT COUNT(*) FROM `{$p}lk_bak_customer`") - $count("SELECT COUNT(*) FROM `{$p}lk_vernut`");

$parts = array();
$lost = 0;
foreach ($TABLES as $t) {
    if (!$exists('lk_bak_' . $t)) {
        continue;
    }
    if (!$m->query("INSERT IGNORE INTO `{$p}{$t}` SELECT b.* FROM `{$p}lk_bak_{$t}` b JOIN `{$p}lk_vernut` r ON r.customer_id = b.customer_id")) {
        $parts[] = $t . ' ОШИБКА: ' . $m->error;
        $lost++;
        continue;
    }
    $parts[] = $t . ' ' . $m->affected_rows;
    // Проверка по первичному ключу: каждая строка копии теперь есть в таблице.
    $cols = array();
    $r = $m->query("SHOW KEYS FROM `{$p}{$t}` WHERE Key_name = 'PRIMARY'");
    while ($r && ($x = $r->fetch_assoc())) {
        $cols[] = $x['Column_name'];
    }
    if (!$cols) {
        $lost++;
        continue;
    }
    $on = array();
    foreach ($cols as $c) {
        $on[] = "x.`$c` = b.`$c`";
    }
    $n = $count("SELECT COUNT(*) FROM `{$p}lk_bak_{$t}` b JOIN `{$p}lk_vernut` r ON r.customer_id = b.customer_id"
        . " LEFT JOIN `{$p}{$t}` x ON " . implode(' AND ', $on) . " WHERE x.`{$cols[0]}` IS NULL");
    $lost += $n === 0 ? 0 : 1;
}
echo 'возвращено строк: ', implode(', ', $parts), "\n";
echo 'кабинетов теперь: ', $count("SELECT COUNT(*) FROM `{$p}customer`"), "\n";
if ($taken === 0 && $lost === 0) {
    foreach ($TABLES as $t) {
        if ($exists('lk_bak_' . $t)) {
            $m->query("DROP TABLE `{$p}lk_bak_{$t}`");
        }
    }
    $m->query("DROP TABLE IF EXISTS `{$p}lk_delete`");
    $m->query("DROP TABLE IF EXISTS `{$p}lk_vernut`");
    echo "вернулось всё; копии {$p}lk_bak_* удалены\n";
} else {
    echo "вернулось не всё: номер занят новым кабинетом - $taken, таблиц с пропусками - $lost; копии {$p}lk_bak_* оставил\n";
}
