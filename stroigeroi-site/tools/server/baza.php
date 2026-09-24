<?php
/*
  Серверная часть правки 22: база. Запускается из командной строки
  (команда в сообщении заказчику), распаковывается вне папки сайта
  и сразу удаляется. Через сайт не работает: первая строка кода
  выходит, если это не командная строка.

  1. Основной номер. 24.09.2026 основным стал 8-963-831-99-99. Прежний,
     8-963-830-09-99, оказался не ошибкой, а номером магазина на
     просп. 50 лет Октября (по карточке 2ГИС). Поэтому в базе меняется
     только настройка магазина config_telephone (её берёт движок,
     например в письмах): в любом виде записи, с сохранением вида.
     Прежнее значение - в таблице phone22_before; она же не даёт
     запустить замену второй раз.
     Правка 21 меняла 830-09-99 на новый номер по всей базе. Если её
     успели запустить (есть таблица phone_before), всё, что она
     заменила, сначала возвращается как было.
  2. Где в базе стоит 8-963-830-09-99 - по всем таблицам магазина,
     у текстов с окружением: номер там может означать и «основной»,
     и «магазин на 50 лет Октября», и решать это надо глазами.
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

echo "-- phone\n";
// Правка 21 заменила бы 830-09-99 по всей базе - вернуть её замены.
$r21 = $m->query("SELECT tbl, where_sql, col, old_value FROM `{$p}phone_before`");
if ($r21) {
    $back = 0;
    $fail = 0;
    while ($row = $r21->fetch_assoc()) {
        if ($m->query('UPDATE `' . $row['tbl'] . '` SET `' . $row['col'] . "` = '" . $e($row['old_value']) . "' WHERE " . $row['where_sql'])) {
            $back++;
        } else {
            $fail++;
        }
    }
    if (!$fail) {
        $m->query("DROP TABLE `{$p}phone_before`");
    }
    echo "правка 21: её замены по всей базе отменены, возвращено $back", $fail ? ", не вышло $fail" : '', "\n";
}
$before = $m->query("SHOW TABLES LIKE '" . $e($p . 'phone22_before') . "'");
$r = $m->query("SELECT setting_id, `value` FROM `{$p}setting` WHERE `key` = 'config_telephone' AND store_id = 0");
$row = $r ? $r->fetch_assoc() : null;
if (!$row) {
    echo "config_telephone: настройки нет\n";
} elseif ($before && $before->num_rows) {
    echo "config_telephone: уже меняли (есть таблица {$p}phone22_before) - сейчас ", $row['value'], "\n";
} else {
    $new = $fix($row['value']);
    if ($new === null || $new === $row['value']) {
        echo 'config_telephone: ', $row['value'], " - прежнего основного номера в нём нет, не менял\n";
    } elseif (!$m->query("CREATE TABLE `{$p}phone22_before` (`tbl` VARCHAR(64) NOT NULL, `where_sql` VARCHAR(255) NOT NULL, `col` VARCHAR(64) NOT NULL, `old_value` MEDIUMTEXT) DEFAULT CHARSET=utf8")
        || !$m->query("INSERT INTO `{$p}phone22_before` VALUES ('" . $e($p . 'setting') . "', '`setting_id` = " . (int)$row['setting_id'] . "', 'value', '" . $e($row['value']) . "')")) {
        echo 'config_telephone STOP: ', $m->error, "\n";
    } elseif ($m->query("UPDATE `{$p}setting` SET `value` = '" . $e($new) . "' WHERE setting_id = " . (int)$row['setting_id'])) {
        echo 'config_telephone: ', $row['value'], ' -> ', $new, "\n";
    } else {
        echo 'config_telephone: ', $m->error, "\n";
    }
}

echo "-- 830-09-99 in texts\n";
$left = 0;
$r = $m->query("SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME LIKE '" . $e($p) . "%' AND TABLE_NAME NOT IN ('" . $e($p . 'phone_before') . "', '" . $e($p . 'phone22_before') . "') AND DATA_TYPE IN ('char','varchar','tinytext','text','mediumtext','longtext')");
while ($r && ($c = $r->fetch_row())) {
    $q = $m->query("SELECT `{$c[1]}` FROM `{$c[0]}` WHERE `{$c[1]}` REGEXP '963[^0-9]{0,8}830[^0-9]{0,8}09[^0-9]{0,8}99'");
    if (!$q || !$q->num_rows) {
        continue;
    }
    $left++;
    $first = $q->fetch_row();
    $text = preg_replace('/\s+/u', ' ', strip_tags(html_entity_decode((string)$first[0], ENT_QUOTES, 'UTF-8')));
    $ctx = '';
    if (preg_match($OLD, $text, $hit, PREG_OFFSET_CAPTURE)) {
        // Смещение у preg - в байтах; режем по байтам только на границе
        // совпадения, а 45 знаков до и 25 после - по буквам.
        $pre = mb_substr(substr($text, 0, $hit[0][1]), -45);
        $post = mb_substr(substr($text, $hit[0][1] + strlen($hit[0][0])), 0, 25);
        $ctx = ' - «' . trim($pre . $hit[0][0] . $post) . '»';
    }
    echo "{$c[0]}.{$c[1]}: ", $q->num_rows, $ctx, "\n";
}
if (!$left) {
    echo "нигде\n";
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
