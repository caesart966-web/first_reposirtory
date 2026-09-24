<?php
/*
  Серверная часть правки 25: знак рубля. В базе у рубля записано
  «&amp;nbsp;руб» - экранировано дважды. Цены движок раскрывает один раз,
  и выходит неразрывный пробел, а фильтр OCFilter экранирует сам и
  показывает покупателю «&nbsp;руб» буквами. Знак меняется на настоящий
  неразрывный пробел и «руб» - так он одинаково выглядит везде.
  Меняется, только если сейчас там то, что видели 24.09.2026; иначе STOP.
  Прежнее значение - в таблице currency_before (она же не даёт поменять
  дважды), откат - valuta-otkat.php.

  Запуск: php valuta.php <папка сайта>
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
echo "-- currency\n";
$want = "\xc2\xa0руб";
$r = $m->query("SELECT currency_id, symbol_right FROM `{$p}currency` WHERE code = 'RUB'");
$row = $r ? $r->fetch_assoc() : null;
if (!$row) {
    echo "STOP: рубля в валютах нет - ничего не менял\n";
    exit(1);
}
$now = $row['symbol_right'];
if ($now === $want) {
    echo "RUB: знак уже исправлен (неразрывный пробел + руб)\n";
} elseif ($now !== '&amp;nbsp;руб' && $now !== '&nbsp;руб') {
    echo 'STOP: у рубля сейчас [', $now, "] - не то, что видели, не трогаю\n";
} elseif (!$m->query("CREATE TABLE `{$p}currency_before` AS SELECT * FROM `{$p}currency` WHERE code = 'RUB'")) {
    echo 'STOP: ', $m->error, " - уже меняли? не трогаю\n";
} elseif ($m->query("UPDATE `{$p}currency` SET symbol_right = '" . $m->real_escape_string($want) . "' WHERE currency_id = " . (int)$row['currency_id'])) {
    echo 'RUB: [', $now, '] -> [неразрывный пробел + руб], hex ', bin2hex($want), ", прежнее - в {$p}currency_before\n";
} else {
    echo 'SQL: ', $m->error, "\n";
}
