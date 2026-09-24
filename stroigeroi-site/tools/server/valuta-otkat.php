<?php
/*
  Откат valuta.php: возвращает прежний знак рубля из таблицы
  currency_before и удаляет её. Только из командной строки.
  Запуск: php valuta-otkat.php <папка сайта>
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
if (!$m->query("SELECT 1 FROM `{$p}currency_before` LIMIT 1")) {
    echo "нет таблицы {$p}currency_before - откатывать нечего\n";
    exit;
}
if ($m->query("UPDATE `{$p}currency` c JOIN `{$p}currency_before` b ON b.currency_id = c.currency_id SET c.symbol_right = b.symbol_right")) {
    echo 'возвращено строк: ', $m->affected_rows, "\n";
    $m->query("DROP TABLE `{$p}currency_before`");
    echo "таблица {$p}currency_before удалена\n";
} else {
    echo 'SQL: ', $m->error, "\n";
}
