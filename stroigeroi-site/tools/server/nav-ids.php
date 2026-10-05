<?php
/*
  Серверная часть правки 35: номера страниц «О компании» и «Юридическим
  лицам» для синей строки шапки. Запускается из командной строки (команда
  в сообщении заказчику) и сразу удаляется; через сайт не работает.

  Ссылка на текстовую страницу движка - это её номер (information_id),
  а номеров этих страниц в репозитории нет: страницы заводились в админке.
  Шапка (header.twig) и меню для телефона (menu.twig) выводят пункт, только
  когда номер не 0, - поэтому скрипт ищет страницу по точному заголовку
  и вписывает номер в строку {% set id_about = 0 %} (id_b2b - для юрлиц).
  Не нашлась ровно одна страница - номер остаётся 0, пункта нет, а скрипт
  пишет, сколько нашлось. Ни имён, ни текстов страниц не печатает.

  Повторный запуск ничего не портит: номер переписывается тем же.

  Запуск: php nav-ids.php <папка сайта>
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
echo "-- nav\n";

$pages = array(
    'id_about' => 'О компании',
    'id_b2b' => 'Юридическим лицам',
);
$found = array();
foreach ($pages as $var => $title) {
    $r = $m->query("SELECT DISTINCT d.information_id FROM `{$p}information_description` d"
        . " JOIN `{$p}information` i ON i.information_id = d.information_id"
        . " WHERE i.status = 1 AND d.title = '" . $m->real_escape_string($title) . "'");
    $n = $r ? $r->num_rows : 0;
    if ($n === 1) {
        $row = $r->fetch_row();
        $found[$var] = (int)$row[0];
        echo $var, ' = ', $found[$var], "\n";
    } else {
        $found[$var] = 0;
        echo $var, ': найдено страниц ', $n, ' - пункта не будет', "\n";
    }
}

$dir = $site . '/catalog/view/theme/stroigeroi2026/template/common/';
foreach (array('header.twig', 'menu.twig') as $name) {
    $file = $dir . $name;
    $src = @file_get_contents($file);
    if ($src === false) {
        echo "STOP: нет файла {$name}\n";
        exit(1);
    }
    $out = $src;
    foreach ($found as $var => $id) {
        $out = preg_replace('/\{% set ' . $var . ' = \d+ %\}/', '{% set ' . $var . ' = ' . $id . ' %}', $out, -1, $hits);
        if ($hits !== 1) {
            echo "STOP: в {$name} строка {$var} встречается {$hits} раз - файл не тронут\n";
            exit(1);
        }
    }
    if ($out !== $src) {
        file_put_contents($file, $out);
    }
    echo $name, ' ok', "\n";
}
