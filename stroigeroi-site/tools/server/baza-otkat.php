<?php
/*
  Откат замены номера из baza.php: возвращает прежние значения из таблиц
  phone22_before (правка 22) и phone_before (правка 21) и удаляет их.
  Только из командной строки; через сайт не работает.
  Запуск: php baza-otkat.php <папка сайта>
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
foreach (array('phone22_before', 'phone_before') as $name) {
    $b = DB_PREFIX . $name;
    $r = $m->query("SELECT tbl, where_sql, col, old_value FROM `$b`");
    if (!$r) {
        continue;
    }
    $ok = 0;
    $bad = 0;
    while ($row = $r->fetch_assoc()) {
        $sql = 'UPDATE `' . $row['tbl'] . '` SET `' . $row['col'] . "` = '" . $m->real_escape_string($row['old_value']) . "' WHERE " . $row['where_sql'];
        if ($m->query($sql)) {
            $ok++;
        } else {
            echo $row['tbl'], ': ', $m->error, "\n";
            $bad++;
        }
    }
    echo "$b: возвращено значений $ok", $bad ? ", не вышло $bad" : '', "\n";
    if (!$bad) {
        $m->query("DROP TABLE `$b`");
        echo "таблица $b удалена\n";
    }
    $done = true;
}
if (empty($done)) {
    echo "нет таблиц phone22_before и phone_before - откатывать нечего\n";
}
