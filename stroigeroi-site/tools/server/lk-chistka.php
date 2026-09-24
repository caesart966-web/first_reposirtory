<?php
/*
  Удаление фальшивых кабинетов (решение заказчика 24.09.2026).

  По lk-schet.php: кабинетов 4966, заказывали из них двое; людям
  регистрация закрыта ещё до нас (403 в .htaccess), а кабинеты заводились
  по 5-10 в день через обходной адрес /create-account, закрытый 23.09.
  Все 4966 «подписаны на рассылку»: одна рассылка из админки - и магазин
  написал бы тысячам случайных адресов.

  Удаляется кабинет, за которым нет НИЧЕГО настоящего: ни одного заказа
  (любого, даже брошенного), возврата, отзыва, бонусов, начислений,
  купона, партнёрской записи. Остаётся и всё, чего касался человек
  в админке: комментарий администратора, отметка safe, группа покупателей
  не та, что по умолчанию, - в такую группу сам не зарегистрируешься,
  так ставят оптовиков. Почему оставлен каждый - печатается числами.

  Вместе с кабинетом удаляются его адреса, корзина, избранное, журнал
  входов и IP, как это делает сама админка (admin/model/customer/customer.php,
  deleteCustomer), плюс таблицы корзины, избранного, онлайна и поиска.
  Другие таблицы с номером покупателя (от модулей) не трогаются - только
  называются в отчёте.

  Прежде чем удалять, всё удаляемое копируется в таблицы lk_bak_*,
  а список номеров - в lk_delete (она же не даёт запустить дважды).
  Откат - lk-chistka-otkat.php. Когда станет ясно, что откат не нужен,
  копии удаляет «php lk-chistka.php <папка сайта> --drop-backup»:
  в копиях те же почты, и хранить их незачем.

  Печатает только числа и названия групп - ни имён, ни почт.

  Запуск: php lk-chistka.php <папка сайта> [--drop-backup]
*/
if (PHP_SAPI !== 'cli') {
    exit;
}
$site = isset($argv[1]) ? rtrim($argv[1], '/') : '.';
$drop = isset($argv[2]) && $argv[2] === '--drop-backup';
require $site . '/config.php';
mysqli_report(MYSQLI_REPORT_OFF);
$m = @new mysqli(DB_HOSTNAME, DB_USERNAME, DB_PASSWORD, DB_DATABASE, (int)DB_PORT);
if ($m->connect_error) {
    echo 'DB: ', $m->connect_error, "\n";
    exit(1);
}
$m->set_charset('utf8');
// Режим, в котором работает сам движок (system/library/db/mysqli.php):
// копии строк пишутся по тем же правилам, по которым их записал магазин.
$m->query("SET SESSION sql_mode = 'NO_ZERO_IN_DATE,NO_ENGINE_SUBSTITUTION'");
$p = DB_PREFIX;
echo "-- cleanup\n";

$exists = function ($t) use ($m, $p) {
    $r = $m->query("SHOW TABLES LIKE '" . $m->real_escape_string($p . $t) . "'");
    return $r && $r->num_rows > 0;
};
$count = function ($sql) use ($m) {
    $r = $m->query($sql);
    return $r ? (int)$r->fetch_row()[0] : -1;
};

// Что удаляется вместе с кабинетом.
$TABLES = array('customer', 'address', 'cart', 'customer_activity', 'customer_approval', 'customer_ip',
                'customer_online', 'customer_search', 'customer_wishlist');

if ($drop) {
    $n = 0;
    foreach ($TABLES as $t) {
        if ($exists('lk_bak_' . $t) && $m->query("DROP TABLE `{$p}lk_bak_{$t}`")) {
            $n++;
        }
    }
    foreach (array('lk_delete', 'lk_vernut') as $t) {
        if ($exists($t)) {
            $m->query("DROP TABLE `{$p}{$t}`");
        }
    }
    echo "копии удалены: таблиц $n; откат больше невозможен\n";
    exit;
}

if (!$exists('customer') || !$exists('order')) {
    echo "STOP: нет таблиц покупателей или заказов - ничего не менял\n";
    exit(1);
}
$r = $m->query("SELECT `value` FROM `{$p}setting` WHERE store_id = 0 AND `key` = 'config_customer_group_id'");
$group = $r && ($x = $r->fetch_row()) ? (int)$x[0] : 0;
if ($group <= 0) {
    echo "STOP: в настройках нет группы покупателей по умолчанию - ничего не менял\n";
    exit(1);
}

// Почему кабинет настоящий: хоть одно условие - кабинет остаётся.
$has = function ($t, $extra = '') use ($p) {
    return "EXISTS (SELECT 1 FROM `{$p}{$t}` k WHERE k.customer_id = c.customer_id$extra)";
};
$why = array('с заказом' => $has('order', ' AND k.order_status_id > 0'),
             'с брошенным заказом' => $has('order', ' AND k.order_status_id = 0'));
foreach (array('return' => 'с возвратом', 'review' => 'с отзывом', 'customer_reward' => 'с бонусами',
               'customer_transaction' => 'с движением по балансу', 'coupon_history' => 'с купоном',
               'customer_affiliate' => 'партнёр', 'customer_history' => 'с комментарием администратора') as $t => $label) {
    if ($exists($t)) {
        $why[$label] = $has($t);
    }
}
$r = $m->query("SHOW COLUMNS FROM `{$p}customer` LIKE 'safe'");
if ($r && $r->num_rows > 0) {
    $why['с отметкой safe'] = 'c.safe = 1';
}
$why['в другой группе'] = "c.customer_group_id <> $group";

if (!$m->query("CREATE TABLE `{$p}lk_delete` (customer_id INT NOT NULL PRIMARY KEY)")) {
    echo 'STOP: ', $m->error, " - уже чистили? ничего не менял\n";
    exit(1);
}
if (!$m->query("INSERT INTO `{$p}lk_delete` SELECT c.customer_id FROM `{$p}customer` c WHERE NOT ("
    . implode(') AND NOT (', $why) . ')')) {
    $err = $m->error;
    $m->query("DROP TABLE `{$p}lk_delete`");
    echo "STOP: список не составился ($err) - ничего не менял\n";
    exit(1);
}

$total = $count("SELECT COUNT(*) FROM `{$p}customer`");
$del = $count("SELECT COUNT(*) FROM `{$p}lk_delete`");
$keep = $total - $del;
$buyers = $count("SELECT COUNT(DISTINCT o.customer_id) FROM `{$p}order` o JOIN `{$p}customer` c ON c.customer_id = o.customer_id");
echo "кабинетов: $total, удаляю: $del, оставляю: $keep\n";
$parts = array();
foreach ($why as $label => $sql) {
    $n = $count("SELECT COUNT(*) FROM `{$p}customer` c WHERE $sql");
    if ($n !== 0) {
        $parts[] = "$label $n";
    }
}
echo 'почему оставлены: ', $parts ? implode(', ', $parts) : '-', "\n";
$r = $m->query("SELECT COUNT(DISTINCT c.customer_id), MAX(g.name) FROM `{$p}customer` c LEFT JOIN `{$p}customer_group_description` g"
    . " ON g.customer_group_id = c.customer_group_id WHERE c.customer_group_id <> $group GROUP BY c.customer_group_id");
while ($r && ($x = $r->fetch_row())) {
    echo '  в группе «', $x[1] === null ? '?' : html_entity_decode($x[1], ENT_QUOTES, 'UTF-8'), '»: ', $x[0], "\n";
}
if ($del <= 0 || $keep < 1 || $keep < $buyers) {
    $m->query("DROP TABLE `{$p}lk_delete`");
    echo "STOP: удалять нечего или счёт не сходится - ничего не менял\n";
    exit(1);
}

// Сначала копии всего удаляемого; не вышла хоть одна - всё назад и STOP.
$made = array();
foreach ($TABLES as $t) {
    if (!$exists($t)) {
        continue;
    }
    if (!$m->query("CREATE TABLE `{$p}lk_bak_{$t}` AS SELECT x.* FROM `{$p}{$t}` x JOIN `{$p}lk_delete` d ON d.customer_id = x.customer_id")) {
        $err = $m->error;
        foreach ($made as $b) {
            $m->query("DROP TABLE `{$p}lk_bak_{$b}`");
        }
        $m->query("DROP TABLE `{$p}lk_delete`");
        echo "STOP: копия $t не записалась ($err) - ничего не менял\n";
        exit(1);
    }
    $made[] = $t;
}
$parts = array();
foreach ($made as $t) {
    $parts[] = $t . ' ' . $count("SELECT COUNT(*) FROM `{$p}lk_bak_{$t}`");
}
echo 'копия записана: ', implode(', ', $parts), "\n";

$parts = array();
foreach ($made as $t) {
    if ($m->query("DELETE x FROM `{$p}{$t}` x JOIN `{$p}lk_delete` d ON d.customer_id = x.customer_id")) {
        $parts[] = $t . ' ' . $m->affected_rows;
    } else {
        $parts[] = $t . ' ОШИБКА: ' . $m->error;
    }
}
echo 'удалено строк: ', implode(', ', $parts), "\n";
echo 'кабинетов осталось: ', $count("SELECT COUNT(*) FROM `{$p}customer`"),
     ', подписаны на рассылку: ', $count("SELECT COUNT(*) FROM `{$p}customer` WHERE newsletter = 1"), "\n";

// Таблицы модулей с номером покупателя: не трогаю, только называю.
$known = array_merge($TABLES, array('order', 'return', 'review', 'customer_reward', 'customer_transaction',
                                    'coupon_history', 'customer_affiliate', 'customer_history', 'lk_delete', 'lk_vernut'));
$r = $m->query("SELECT TABLE_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND COLUMN_NAME = 'customer_id'");
while ($r && ($x = $r->fetch_row())) {
    $name = $x[0];
    if (strpos($name, $p) !== 0 || in_array(substr($name, strlen($p)), $known, true) || strpos($name, $p . 'lk_bak_') === 0) {
        continue;
    }
    $n = $count("SELECT COUNT(*) FROM `$name` x JOIN `{$p}lk_delete` d ON d.customer_id = x.customer_id");
    if ($n > 0) {
        echo "не трогал: $name - строк у удалённых $n\n";
    }
}
echo "откат - lk-chistka-otkat.php; копии в таблицах {$p}lk_bak_*\n";
