<?php
/*
  Откат yurlicam.php: возвращает прежний текст страницы «Юридическим лицам»
  из таблицы legal_before и удаляет её. Только из командной строки.
  Запуск: php yurlicam-otkat.php <папка сайта>
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
if (!$m->query("SELECT 1 FROM `{$p}legal_before` LIMIT 1")) {
    echo "нет таблицы {$p}legal_before - откатывать нечего\n";
    exit;
}
if ($m->query("UPDATE `{$p}information_description` d JOIN `{$p}legal_before` b ON b.information_id = d.information_id AND b.language_id = d.language_id SET d.description = b.description")) {
    echo 'возвращено строк: ', $m->affected_rows, "\n";
    $m->query("DROP TABLE `{$p}legal_before`");
    echo "таблица {$p}legal_before удалена\n";
} else {
    echo 'SQL: ', $m->error, "\n";
}
