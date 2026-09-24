<?php
/*
  Серверная часть правки 21: база. Запускается из командной строки
  (команда в сообщении заказчику), распаковывается вне папки сайта
  и сразу удаляется. Через сайт не работает: первая строка кода
  выходит, если это не командная строка.

  1. Номер телефона. 24.09.2026 заказчик сменил номер 8-963-830-09-99
     на 8-963-831-99-99. В теме он поменян в файлах, здесь - в базе:
     настройки магазина (config_telephone и любые другие), модули,
     текстовые страницы, описания товаров и разделов, магазины
     (location), баннеры, правки темы из админки. Запись в любом виде -
     «+7 (963) 830-09-99», «8 963 830 09 99», «+79638300999»,
     с &nbsp; - меняется с сохранением вида: переставляются только
     цифры, длина строки та же (важно для сериализованных настроек).
     Заказы и покупатели не трогаются: номер в них - история.
     Прежние значения - в таблице phone_before; она же не даёт
     запустить замену второй раз.
  2. Где в базе старый номер ещё остался - по всем таблицам магазина.
  3. Знак валюты, как он записан (у рубля видели «&nbsp;руб» текстом).
  4. Текстовые страницы: номер, название, включена, в подвале, длина
     текста, адрес.

  Пароль базы читается из config.php и никуда не выводится.
  Код - без конструкций новее PHP 7.4.

  Запуск: php baza.php <папка сайта>
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
$e = function ($s) use ($m) { return $m->real_escape_string($s); };

$SEP = '(?:[\s()\-]|&nbsp;|&#160;)*';
$OLD = '/((?:\+?7|8)' . $SEP . ')?963(' . $SEP . ')830(' . $SEP . ')09(' . $SEP . ')99/u';
$fix = function ($s) use ($OLD) {
    return preg_replace_callback($OLD, function ($x) {
        return $x[1] . '963' . $x[2] . '831' . $x[3] . '99' . $x[4] . '99';
    }, $s);
};

function text_columns($m, $table) {
    $cols = array();
    $r = $m->query("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '" . $m->real_escape_string($table) . "' AND DATA_TYPE IN ('char','varchar','tinytext','text','mediumtext','longtext')");
    while ($r && ($c = $r->fetch_row())) {
        $cols[] = $c[0];
    }
    return $cols;
}

function key_columns($m, $table) {
    $cols = array();
    $r = $m->query("SHOW KEYS FROM `" . $table . "` WHERE Key_name = 'PRIMARY'");
    while ($r && ($c = $r->fetch_assoc())) {
        $cols[] = $c['Column_name'];
    }
    return $cols;
}

echo "-- phone\n";
$before = $m->query("SHOW TABLES LIKE '" . $e($p . 'phone_before') . "'");
if ($before && $before->num_rows) {
    echo "уже меняли: есть таблица {$p}phone_before, замену не повторяю\n";
} elseif (!$m->query("CREATE TABLE `{$p}phone_before` (`tbl` VARCHAR(64) NOT NULL, `where_sql` VARCHAR(255) NOT NULL, `col` VARCHAR(64) NOT NULL, `old_value` MEDIUMTEXT) DEFAULT CHARSET=utf8")) {
    echo 'STOP: ', $m->error, "\n";
} else {
    $targets = array('setting', 'module', 'information_description', 'product_description',
                     'category_description', 'location', 'banner_image', 'theme');
    $total = 0;
    foreach ($targets as $t) {
        $table = $p . $t;
        $cols = text_columns($m, $table);
        $keys = key_columns($m, $table);
        if (!$cols || !$keys) {
            continue;
        }
        $like = array();
        foreach ($cols as $c) {
            $like[] = "`$c` LIKE '%963%'";
        }
        $r = $m->query("SELECT * FROM `$table` WHERE " . implode(' OR ', $like));
        if (!$r) {
            echo "$table: ", $m->error, "\n";
            continue;
        }
        $rows = 0;
        while ($row = $r->fetch_assoc()) {
            $set = array();
            foreach ($cols as $c) {
                if ($row[$c] === null || strpos($row[$c], '963') === false) {
                    continue;
                }
                $new = $fix($row[$c]);
                if ($new === null) {
                    echo "$table.$c: текст не разобрать (кодировка) - пропущено\n";
                    continue;
                }
                if ($new !== $row[$c]) {
                    $set[$c] = $new;
                }
            }
            if (!$set) {
                continue;
            }
            $where = array();
            foreach ($keys as $k) {
                $where[] = "`$k` = '" . $e($row[$k]) . "'";
            }
            $where = implode(' AND ', $where);
            $saved = true;
            foreach ($set as $c => $new) {
                $saved = $saved && $m->query("INSERT INTO `{$p}phone_before` VALUES ('" . $e($table) . "', '" . $e($where) . "', '" . $e($c) . "', '" . $e($row[$c]) . "')");
            }
            if (!$saved) {
                echo "$table: копию не сохранить (", $m->error, ") - строка не тронута\n";
                continue;
            }
            $upd = array();
            foreach ($set as $c => $new) {
                $upd[] = "`$c` = '" . $e($new) . "'";
            }
            if (!$m->query("UPDATE `$table` SET " . implode(', ', $upd) . " WHERE $where")) {
                echo "$table: ", $m->error, "\n";
                continue;
            }
            $rows++;
            if ($t === 'setting') {
                echo '  ', $row['key'], ': ', mb_substr(strip_tags($set['value']), 0, 60), "\n";
            }
        }
        if ($rows) {
            echo "$table: строк изменено $rows\n";
            $total += $rows;
        }
    }
    echo $total ? "всего строк: $total\n" : "в базе старого номера не было\n";
}
$r = $m->query("SELECT `value` FROM `{$p}setting` WHERE `key` = 'config_telephone' AND store_id = 0");
echo 'config_telephone: ', ($r && ($row = $r->fetch_row())) ? $row[0] : '?', "\n";

echo "-- phone left\n";
$left = 0;
$r = $m->query("SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE '" . $e($p) . "%' AND TABLE_NAME <> '" . $e($p . 'phone_before') . "' AND DATA_TYPE IN ('char','varchar','tinytext','text','mediumtext','longtext')");
while ($r && ($c = $r->fetch_row())) {
    $q = $m->query("SELECT COUNT(*) FROM `{$c[0]}` WHERE `{$c[1]}` REGEXP '963[^0-9]{0,8}830[^0-9]{0,8}09[^0-9]{0,8}99'");
    if ($q && ($n = (int)$q->fetch_row()[0])) {
        echo "{$c[0]}.{$c[1]}: $n\n";
        $left++;
    }
}
if (!$left) {
    echo "старого номера в базе нет нигде\n";
}

echo "-- currency\n";
$r = $m->query("SELECT `value` FROM `{$p}setting` WHERE `key` = 'config_currency' AND store_id = 0");
echo 'default: ', ($r && ($row = $r->fetch_row())) ? $row[0] : '?', "\n";
$r = $m->query("SELECT code, status, symbol_left, symbol_right, decimal_place FROM `{$p}currency` ORDER BY status DESC, code");
while ($r && ($c = $r->fetch_assoc())) {
    echo $c['code'], ' status=', $c['status'], ' left=[', $c['symbol_left'], '] right=[', $c['symbol_right'],
         '] right-hex=', bin2hex($c['symbol_right']), ' decimals=', $c['decimal_place'], "\n";
}

echo "-- pages\n";
$r = $m->query("SELECT i.*, d.title, CHAR_LENGTH(d.description) AS len, (SELECT u.keyword FROM `{$p}seo_url` u WHERE u.query = CONCAT('information_id=', i.information_id) LIMIT 1) AS kw FROM `{$p}information` i JOIN `{$p}information_description` d ON d.information_id = i.information_id ORDER BY i.sort_order, i.information_id");
if (!$r) {
    echo 'SQL: ', $m->error, "\n";
}
while ($r && ($i = $r->fetch_assoc())) {
    echo $i['information_id'], ' [', $i['title'], '] status=', $i['status'], ' footer=',
         isset($i['bottom']) ? $i['bottom'] : '?', ' text=', $i['len'], ' url=/', $i['kw'], "\n";
}
